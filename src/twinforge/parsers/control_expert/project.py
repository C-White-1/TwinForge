"""Conservative basic mapping from captured exchange sections to neutral objects."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from twinforge.model import (
    AddOnInstruction, AddOnInstructionParameter, Chassis, Controller, Datatype, DatatypeMember,
    Identity, Module, Program, Resource, Routine, SourceExtension, StructuredTextLine, Tag, Task,
)
from twinforge.schema.control_expert.mapping import BASIC_MAPPING, MappingSpec, PathSpec
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC
from twinforge.analysis.execution_order import resolve_fbd_execution_order
from twinforge.analysis.graphical_bindings import (
    member_path_context, resolve_function_block_bindings, resolve_graphical_bindings,
)
from twinforge.analysis.library_calls import match_library_calls
from twinforge.analysis.sequential_bindings import resolve_sequential_bindings
from twinforge.analysis.sfc_connectivity import resolve_sfc_connectivity

from twinforge.model.library_interface import LibraryInterface, LibraryParameter
from twinforge.model.sequential import SequentialElement

from .capture import CapturedArtifact, CapturedSection, Diagnostic, SourceLocation
from .graphical import parse_diagrams
from .ladder import parse_ladder_rungs, resolve_ladder_pin_conditions
from .sfc import parse_charts
from .evidence import source_extension as _extension


def _apply_ladder_pin_conditions(
    result: "ParsedProject", routine: Routine, bindings: list, source: CapturedSection,
) -> None:
    for binding in bindings:
        if binding.network_index >= len(routine.graphical_diagrams):
            continue
        diagram = routine.graphical_diagrams[binding.network_index]
        matches = [obj for obj in diagram.objects if obj.kind == "block" and obj.position == binding.position]
        if len(matches) != 1:
            result.report("unresolved_ladder_pin_condition",
                          f"No unique block found for a resolved Ladder wire at {binding.position}", source)
            continue
        pins = [pin for pin in matches[0].pins if pin.name == binding.pin_name]
        if len(pins) != 1:
            result.report("unresolved_ladder_pin_condition",
                          f"No unique {binding.pin_name!r} pin found for a resolved Ladder wire at {binding.position}",
                          source)
            continue
        pins[0].ladder_condition = binding.condition


@dataclass
class ParsedProject:
    controller: Controller
    artifact: CapturedArtifact
    diagnostics: list[Diagnostic] = field(default_factory=list)

    library_interfaces: list[LibraryInterface] = field(default_factory=list)

    def report(self, code: str, message: str, node: CapturedSection) -> None:
        self.diagnostics.append(Diagnostic(code, message, node.source))


def _select(node: CapturedSection, path: PathSpec) -> list[CapturedSection]:
    nodes = [node]
    for name in path:
        nodes = [child for parent in nodes for child in parent.ordered_children if child.tag == name]
    return nodes


def _first(node: CapturedSection, path: PathSpec) -> CapturedSection | None:
    nodes = _select(node, path)
    return nodes[0] if len(nodes) == 1 else None


def _attrs(node: CapturedSection | None) -> dict[str, str]:
    return node.raw_attributes if node is not None else {}


def _comment_text(node: CapturedSection, spec: MappingSpec) -> str | None:
    comment = _first(node, spec.comments)
    return comment.text if comment is not None else None


def _location(extension: SourceExtension) -> SourceLocation:
    metadata = extension.metadata
    return SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"])


def _unique_name(
    result: ParsedProject, node: CapturedSection, name: str | None,
    used: set[str], kind: str,
) -> str | None:
    if not name or name.casefold() in used:
        result.report("ambiguous_identity", f"Missing or duplicate {kind} name {name!r}; source retained", node)
        return None
    used.add(name.casefold())
    return name


def _variables(
    result: ParsedProject, root: CapturedSection, spec: MappingSpec,
    known_datatypes: dict[str, Datatype],
) -> None:
    _declare_variables(
        result, _select(root, spec.variables), spec, known_datatypes, set(), result.controller.add_tag)


def _resources(
    result: ParsedProject, root: CapturedSection, spec: MappingSpec,
    known_datatypes: dict[str, Datatype],
) -> None:
    """Capture each resource's own variables; they are not merged into controller tags."""
    used_names: set[str] = set()
    for node in _select(root, spec.resources):
        name = _unique_name(result, node, node.raw_attributes.get(spec.resource_name_attribute), used_names, "resource")
        if name is None:
            continue
        resource = Resource(
            name=name, identifier=node.raw_attributes.get(spec.resource_identifier_attribute),
            source_extensions=[_extension(node)])
        declarations = [variable for path in spec.resource_variables for variable in _select(node, path)]
        counts: dict[str, int] = {}
        for variable in declarations:
            key = variable.raw_attributes.get("name", "").casefold()
            counts[key] = counts.get(key, 0) + 1
        resource.ambiguous_names = {key for key, count in counts.items() if key and count > 1}

        def register(tag: Tag, resource: Resource = resource) -> None:
            tag.metadata["declaration_scope"] = "resource"
            tag.metadata["resource"] = resource.name
            resource.add_tag(tag)

        _declare_variables(result, declarations, spec, known_datatypes, set(), register)
        result.controller.add_resource(resource)


def _declare_variables(
    result: ParsedProject, nodes: list[CapturedSection], spec: MappingSpec,
    known_datatypes: dict[str, Datatype], used: set[str], register,
) -> None:
    for node in nodes:
        attrs = node.raw_attributes
        name = _unique_name(result, node, attrs.get("name"), used, "variable")
        if name is None:
            continue
        type_name = attrs.get("typeName")
        comment = _first(node, spec.comments)
        tag = Tag(name=name, data_type=type_name,
                  description=comment.text if comment else None,
                  source_extensions=[_extension(node)])
        # Address is a source memory binding, never an alias to another symbol.
        if "topologicalAddress" in attrs:
            tag.metadata["source_memory_address"] = attrs["topologicalAddress"]
        initializers = _select(node, spec.initializers)
        if initializers:
            tag.metadata["source_initial_values"] = [dict(n.raw_attributes) for n in initializers]
            result.report("uninterpreted_initial_value", f"{name}: initializer retained lexically", node)
        match = re.fullmatch(spec.array_pattern, type_name or "", flags=re.IGNORECASE)
        base_type = type_name
        if match:
            lower, upper = int(match[1]), int(match[2])
            base_type = match[3]
            if upper < lower:
                result.report("invalid_array_bounds", f"{name}: upper bound precedes lower bound", node)
            else:
                tag.metadata["source_array_bounds"] = [[lower, upper]]
                tag.metadata["source_array_element_type"] = base_type
            # The model has no typed lower-bound field. Do not normalize this
            # into a zero-based dimensions string and imply portability.
            result.report("unresolved_array_type", f"{name}: array expression and bounds retained; type not resolved", node)
        if base_type:
            tag.data_type_definition = known_datatypes.get(base_type.casefold())
        if tag.data_type_definition is None and (not base_type or base_type.upper() not in spec.scalar_types):
            result.report("unresolved_type", f"{name}: no supported type definition for {base_type!r}", node)
        register(tag)


def _datatypes(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> dict[str, Datatype]:
    """Map derived type definitions; members may forward-reference any DDT by name."""
    used: set[str] = set()
    by_key: dict[str, Datatype] = {}
    pending: list[CapturedSection] = []
    for node in _select(root, spec.datatypes):
        name = _unique_name(result, node, node.raw_attributes.get(spec.datatype_name_attribute), used, "datatype")
        if name is None:
            continue
        comment = _first(node, spec.comments)
        datatype = Datatype(name=name, description=comment.text if comment else None,
                            source_extensions=[_extension(node)])
        result.controller.add_datatype(datatype)
        by_key[name.casefold()] = datatype
        pending.append(node)
    for node in pending:
        datatype = by_key[node.raw_attributes[spec.datatype_name_attribute].casefold()]
        member_used: set[str] = set()
        for member_node in _select(node, spec.datatype_members):
            attrs = member_node.raw_attributes
            member_name = _unique_name(result, member_node, attrs.get("name"), member_used, "datatype member")
            if member_name is None:
                continue
            type_name = attrs.get("typeName")
            comment = _first(member_node, spec.comments)
            match = re.fullmatch(spec.array_pattern, type_name or "", flags=re.IGNORECASE)
            base_type, dimension = type_name, None
            label = f"{datatype.name}.{member_name}"
            if match:
                lower, upper = int(match[1]), int(match[2])
                base_type = match[3]
                if upper < lower:
                    result.report("invalid_array_bounds", f"{label}: upper bound precedes lower bound", member_node)
                else:
                    # Retain the lexical bounds as written; do not zero-base or
                    # otherwise normalize a lower bound that may not be zero.
                    dimension = f"{lower}..{upper}"
                result.report("unresolved_array_type", f"{label}: array expression and bounds retained; type not resolved", member_node)
            member = DatatypeMember(name=member_name, data_type_name=base_type, dimension=dimension,
                                    description=comment.text if comment else None,
                                    source_extensions=[_extension(member_node)])
            if base_type:
                member.data_type = by_key.get(base_type.casefold())
            if member.data_type is None and (not base_type or base_type.upper() not in spec.scalar_types):
                result.report("unresolved_type", f"{label}: no supported type definition for {base_type!r}", member_node)
            datatype.members.append(member)
    return by_key


def _function_blocks(
    result: ParsedProject, root: CapturedSection, spec: MappingSpec,
    known_datatypes: dict[str, Datatype],
) -> None:
    """Map user-defined Function Block (DFB) definitions: interface, locals and body.

    A crypted body is genuinely opaque; only the interface is retained. Body
    bindings (pin/symbol resolution) are not attempted here -- an FB body's
    parameters and locals form their own namespace, not the project's global
    tags, and the existing binding analyses assume one flat global scope.
    """
    used: set[str] = set()
    for node in _select(root, spec.function_blocks):
        name = _unique_name(result, node, node.raw_attributes.get(spec.function_block_name_attribute), used, "function block")
        if name is None:
            continue
        comment = _first(node, spec.comments)
        aoi = AddOnInstruction(name=name, description=comment.text if comment else None,
                               source_extensions=[_extension(node)])
        param_used: set[str] = set()
        for path, direction in spec.library_parameters:
            for parameter in _select(node, path):
                attrs = parameter.raw_attributes
                pname = _unique_name(result, parameter, attrs.get("name"), param_used, "function block parameter")
                if pname is None:
                    continue
                type_name = attrs.get("typeName")
                aoi.add_parameter(AddOnInstructionParameter(
                    name=pname, data_type=type_name, usage=direction,
                    data_type_definition=known_datatypes.get(type_name.casefold()) if type_name else None,
                    source_extensions=[_extension(parameter)],
                ))
        local_used: set[str] = set()
        # Public vs private is a real Control Expert distinction (separate XML
        # sections), not an evidence gap -- retained so a public local, unlike
        # a private one, can later be proven reachable from outside the FB
        # (see the public local member-path checkpoint).
        for path, visibility in ((spec.function_block_public_locals, "public"),
                                 (spec.function_block_private_locals, "private")):
            for local_node in _select(node, path):
                attrs = local_node.raw_attributes
                lname = _unique_name(result, local_node, attrs.get("name"), local_used, "function block local variable")
                if lname is None:
                    continue
                type_name = attrs.get("typeName")
                local_tag = Tag(
                    name=lname, data_type=type_name,
                    data_type_definition=known_datatypes.get(type_name.casefold()) if type_name else None,
                    source_extensions=[_extension(local_node)],
                )
                local_tag.metadata["visibility"] = visibility
                aoi.add_local_tag(local_tag)
        programs = _select(node, spec.function_block_program)
        crypted = _first(node, spec.function_block_crypted)
        if crypted is not None:
            result.report("encrypted_function_block_body",
                          f"{name}: implementation body is encrypted; interface retained", node)
        elif programs:
            names = [program.raw_attributes.get("name", "").casefold() for program in programs]
            if len(programs) > 1 and (not all(names) or len(set(names)) != len(names)):
                # Sections that cannot be told apart by name are not guessed at.
                result.report("ambiguous_function_block_body",
                              f"{name}: {len(programs)} implementation sections without distinct names", node)
            else:
                for index, program in enumerate(programs):
                    # A lone body keeps the block's own name; several are keyed by section name.
                    routine_name = name if len(programs) == 1 else program.raw_attributes["name"]
                    routine = _function_block_routine(result, spec, name, routine_name, program)
                    if routine is None:
                        continue
                    if len(programs) > 1:
                        # Section order is recorded, never treated as an execution claim.
                        routine.metadata["function_block_section"] = {"index": index, "count": len(programs)}
                    aoi.add_routine(routine)
        else:
            result.report("unresolved_function_block_body", f"{name}: no supported implementation body found", node)
        result.controller.add_add_on_instruction(aoi)


def _function_block_routine(
    result: ParsedProject, spec: MappingSpec, name: str, routine_name: str, program: CapturedSection,
) -> Routine | None:
    sources = [(source, language) for tag, language in spec.languages for source in _select(program, (tag,))]
    if len(sources) != 1:
        result.report("ambiguous_language", f"{name}: expected one supported source body, found {len(sources)}", program)
        return None
    source, language = sources[0]
    routine = Routine(name=routine_name, language=language, source_extensions=[_extension(source)])
    conditions = _section_conditions(result, program, spec, None, name)
    if conditions:
        routine.metadata["section_conditions"] = conditions
    if language == "ST":
        routine.structured_text_lines = [
            StructuredTextLine(number=index + 1, text=line)
            for index, line in enumerate((source.text or "").split("\n"))
        ]
        if source.ordered_children:
            result.report("unsupported_st_structure", f"{name}: nested ST content retained as evidence", source)
    elif language == "SFC":
        routine.sequential_charts, diagnostics = parse_charts(program)
        result.diagnostics.extend(diagnostics)
        result.report("uninterpreted_sfc_execution", f"{name}: chart structure retained; connectivity and execution unresolved", source)
    else:
        routine.graphical_diagrams, diagnostics = parse_diagrams(source)
        result.diagnostics.extend(diagnostics)
        result.report("uninterpreted_graphical_logic", f"{name}: {language} retained without execution mapping", source)
        if language == "LD":
            routine.ladder_rungs, ladder_diagnostics = parse_ladder_rungs(source)
            result.diagnostics.extend(ladder_diagnostics)
            pin_bindings, pin_diagnostics = resolve_ladder_pin_conditions(source)
            result.diagnostics.extend(pin_diagnostics)
            _apply_ladder_pin_conditions(result, routine, pin_bindings, source)
    return routine


def _section_conditions(
    result: ParsedProject, ref: CapturedSection, spec: MappingSpec,
    global_names: dict[str, int] | None, label: str,
) -> dict[str, dict[str, str]]:
    """Lexical section activation/logic condition evidence; never evaluated.

    Kept apart from task scheduling and block enable behaviour. The activation
    text is classified only by shape and global-name identity: neither its
    truth value nor the meaning of a logic-condition keyword is interpreted.
    ``global_names`` is None for a Function Block body, whose identifiers belong
    to that block's own namespace and are not resolved against project tags.
    """
    attrs = ref.raw_attributes
    conditions: dict[str, dict[str, str]] = {}
    activation = attrs.get(spec.section_activation_attribute)
    if activation is not None:
        text = activation.strip()
        count = 0 if global_names is None else global_names.get(text.casefold(), 0)
        if re.fullmatch(EXPRESSION_SPEC.direct_address, text):
            binding = "direct_address"
        elif not re.fullmatch(EXPRESSION_SPEC.identifier, text):
            binding = "unresolved_expression"
        elif global_names is None:
            binding = "function_block_scope_unresolved"
        elif count == 1:
            binding = "declared_symbol"
        else:
            binding = "ambiguous_symbol" if count > 1 else "missing_symbol"
        conditions["activation"] = {"text": activation, "binding_kind": binding}
        if binding not in {"declared_symbol", "direct_address"}:
            result.report(
                "unresolved_section_activation_condition",
                f"{label}: activation condition {activation!r}: {binding}", ref)
    logic = attrs.get(spec.section_logic_attribute)
    if logic is not None:
        conditions["logic"] = {"text": logic}
    return conditions


def _programs_and_tasks(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    used: set[str] = set()
    identities: dict[str, tuple[str | None, CapturedSection]] = {}
    ambiguous: set[str] = set()
    section_nodes = _select(root, spec.sections)
    for path in spec.additional_sections:
        section_nodes.extend(_select(root, path))
    for node in section_nodes:
        identity = _first(node, spec.section_identity)
        attrs = _attrs(identity)
        raw_name = attrs.get("name")
        if raw_name and raw_name.casefold() in used:
            ambiguous.add(raw_name.casefold())
        name = _unique_name(result, node, raw_name, used, "section")
        if name is None:
            continue
        # One neutral Program per source section allows Task's ordered program
        # references to express section scheduling without inventing call logic.
        program = Program(name=name, source_extensions=[_extension(node)])
        sources = [(source, language) for tag, language in spec.languages for source in _select(node, (tag,))]
        if len(sources) == 1:
            source, language = sources[0]
            routine = Routine(name=name, language=language, source_extensions=[_extension(source)])
            if language == "ST":
                routine.structured_text_lines = [
                    StructuredTextLine(number=index + 1, text=line)
                    for index, line in enumerate((source.text or "").split("\n"))
                ]
                if source.ordered_children:
                    result.report("unsupported_st_structure", f"{name}: nested ST content retained as evidence", source)
            elif language == "SFC":
                routine.sequential_charts, diagnostics = parse_charts(node)
                result.diagnostics.extend(diagnostics)
                result.report("uninterpreted_sfc_execution", f"{name}: chart structure retained; connectivity and execution unresolved", source)
            else:
                routine.graphical_diagrams, diagnostics = parse_diagrams(source)
                result.diagnostics.extend(diagnostics)
                result.report("uninterpreted_graphical_logic", f"{name}: {language} retained without execution mapping", source)
                if language == "LD":
                    routine.ladder_rungs, ladder_diagnostics = parse_ladder_rungs(source)
                    result.diagnostics.extend(ladder_diagnostics)
                    pin_bindings, pin_diagnostics = resolve_ladder_pin_conditions(source)
                    result.diagnostics.extend(pin_diagnostics)
                    _apply_ladder_pin_conditions(result, routine, pin_bindings, source)
            program.add_routine(routine)
        else:
            result.report("ambiguous_language", f"{name}: expected one supported source body, found {len(sources)}", node)
        result.controller.add_program(program)
        identities[name.casefold()] = (attrs.get("task"), node)

    task_nodes = _select(root, spec.tasks)
    task_resource: dict[int, Resource] = {}
    for resource_node in _select(root, spec.resources):
        resource = result.controller.resources.get(resource_node.raw_attributes.get(spec.resource_name_attribute, ""))
        if resource is not None:
            for task_node in _select(resource_node, spec.resource_tasks):
                task_resource[id(task_node)] = resource
    task_counts: dict[str, int] = {}
    for node in task_nodes:
        key = node.raw_attributes.get("task", "").casefold()
        task_counts[key] = task_counts.get(key, 0) + 1
    used = set()
    programs = {name.casefold(): program for name, program in result.controller.programs.items()}
    scheduled: set[str] = set()
    global_names: dict[str, int] = {}
    for variable in _select(root, spec.variables):
        key = variable.raw_attributes.get("name", "").casefold()
        global_names[key] = global_names.get(key, 0) + 1
    for node in task_nodes:
        attrs = node.raw_attributes
        name = _unique_name(result, node, attrs.get("task"), used, "task")
        if name is None:
            continue
        task = Task(name=name, task_type=attrs.get("taskType"), source_extensions=[_extension(node)])
        # Do not assign rate/watchdog units from undocumented raw values.
        task.metadata["source_task_attributes"] = dict(attrs)
        owner = task_resource.get(id(node))
        if owner is not None:
            task.metadata["resource"] = owner.name
            owner.task_names.append(name)
        if task.task_type == "cyclic":
            task.metadata["cycle_policy"] = "successive_cycles_while_active"
        if task.task_type != "cyclic":
            result.report("unresolved_task_semantics", f"{name}: task mode not covered by observed cyclic samples", node)
        for section_index, ref in enumerate(_select(node, spec.task_sections)):
            target = ref.raw_attributes.get("name", "")
            task.scheduled_program_names.append(target)
            key = target.casefold()
            declared_task = identities.get(key, (None, ref))[0]
            if (not target or key not in programs or key in ambiguous
                    or task_counts[name.casefold()] > 1
                    or declared_task is None or declared_task.casefold() != name.casefold()):
                result.report("unresolved_section_reference", f"{name}: missing, ambiguous or conflicting section {target!r}", ref)
                continue
            task.scheduled_programs.append(programs[key])
            conditions = _section_conditions(
                result, ref, spec, global_names, f"{name}/{target}")
            for routine in programs[key].routines.values():
                entry = {
                    "task_name": name,
                    "task_type": task.task_type,
                    "section_index": section_index,
                    "eligibility": "each_active_task_cycle" if task.task_type == "cyclic" else "task_dependent",
                    "execution_conditions": "not_evaluated",
                }
                if conditions:
                    entry["section_conditions"] = conditions
                routine.metadata.setdefault("task_schedule", []).append(entry)
            scheduled.add(key)
        result.controller.add_task(task)
    for key, (_, node) in identities.items():
        if key not in scheduled:
            result.report("unscheduled_section", "Section has no unambiguous task schedule binding", node)


def _hardware(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    plcs = _select(root, spec.plc)
    if len(plcs) != 1:
        result.report("unresolved_hardware", f"Expected one PLC description, found {len(plcs)}", root)
        return
    plc = plcs[0]
    part = _first(plc, spec.part)
    result.controller.identity = Identity(product_name=_attrs(part).get("partNumber"))
    if part:
        result.controller.identity.source_extensions.append(_extension(part))
    racks = [(rack, layout) for layout in spec.hardware_layouts for rack in _select(plc, layout.racks)]
    if not racks:
        result.report("unresolved_hardware", "No observed rack layout matched; hardware remains in source evidence", plc)
    for index, (rack, layout) in enumerate(racks):
        address = _attrs(_first(rack, spec.equipment)).get("topoAddress")
        # Topological addresses are not network addresses. Generated labels are
        # explicit fallbacks, with source provenance retained for each chassis.
        name = address or f"rack-{index}"
        if name in result.controller.chassis:
            result.report("ambiguous_hardware", f"Repeated rack address {name!r}; using source ordinal", rack)
            name = f"{name}#{index}"
        chassis = Chassis(name=name, source_extensions=[_extension(rack)])
        result.controller.add_chassis(chassis)
        modules = [child for child in rack.ordered_children if child.tag in layout.modules]
        for module_node in modules:
            part = _first(module_node, spec.part)
            equipment = _attrs(_first(module_node, spec.equipment))
            catalog = _attrs(part).get("partNumber", "")
            module = Module(name=catalog, catalog=catalog,
                            identity=Identity(product_name=catalog or None),
                            source_extensions=[_extension(module_node)])
            position = equipment.get("position", "")
            if position.isdecimal():
                module.slot = int(position)
            if not catalog or module.slot is None or module.slot in chassis.modules:
                result.report("unplaced_hardware", f"{catalog!r}: missing identity, special position or conflicting slot", module_node)
                result.controller.add_unplaced_module(module)
            else:
                chassis.add_module(module)
        power_supplies = [child for child in rack.ordered_children if child.tag in layout.power_supply_modules]
        for supply_node in power_supplies:
            part = _first(supply_node, spec.part)
            catalog = _attrs(part).get("partNumber", "")
            supply = Module(name=catalog, catalog=catalog,
                            identity=Identity(product_name=catalog or None),
                            source_extensions=[_extension(supply_node)])
            if not catalog:
                result.report("unplaced_hardware", f"{catalog!r}: missing identity", supply_node)
                result.controller.add_unplaced_module(supply)
            else:
                chassis.add_power_supply(supply)


def parse_project(artifact: CapturedArtifact, *, spec: MappingSpec = BASIC_MAPPING) -> ParsedProject:
    """Map one captured exchange XML; never choose a project from an archive implicitly."""
    root = artifact.section
    if root is None or root.tag not in spec.roots:
        raise ValueError("Expected a captured exchange XML artifact; select a project member explicitly")
    content = _first(root, spec.content)
    name = _attrs(content).get("name", "")
    controller = Controller(name=name, identity=Identity(), source_extensions=[_extension(root)])
    result = ParsedProject(controller, artifact, list(artifact.diagnostics))
    if not name:
        result.report("missing_project_name", "Project name missing or ambiguous", root)
    for tag, name_attribute, kind in spec.library_definitions:
        for node in _select(root, (tag,)):
            result.library_interfaces.append(LibraryInterface(
                node.raw_attributes.get(name_attribute), kind,
                [LibraryParameter(parameter.raw_attributes.get("name"),
                                  parameter.raw_attributes.get("typeName"), direction,
                                  comment=_comment_text(parameter, spec))
                 for path, direction in spec.library_parameters for parameter in _select(node, path)],
                [_extension(node)],
            ))
    known_datatypes = _datatypes(result, root, spec)
    _variables(result, root, spec, known_datatypes)
    _resources(result, root, spec, known_datatypes)
    _function_blocks(result, root, spec, known_datatypes)
    _programs_and_tasks(result, root, spec)
    _hardware(result, root, spec)
    variable_counts: dict[str, int] = {}
    for node in _select(root, spec.variables):
        key = node.raw_attributes.get("name", "").casefold()
        variable_counts[key] = variable_counts.get(key, 0) + 1
    # SFC step names are a project-wide namespace: a "<step>.X" contact in any
    # section can reference a step declared in a different chart's section.
    step_counts: dict[str, int] = {}
    step_names: dict[str, str] = {}

    def _collect_steps(elements: list[SequentialElement]) -> None:
        for element in elements:
            if element.kind == "step":
                name = element.properties.get("name")
                if name:
                    key = name.casefold()
                    step_counts[key] = step_counts.get(key, 0) + 1
                    step_names.setdefault(key, name)
            _collect_steps(element.children)

    for program in controller.programs.values():
        for routine in program.routines.values():
            for chart in routine.sequential_charts:
                _collect_steps(chart.elements)
    member_paths = member_path_context(controller, result.library_interfaces, spec.array_pattern)
    issues = resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, member_paths=member_paths,
        literal_patterns=EXPRESSION_SPEC.literals,
        ambiguous_names=frozenset(key for key, count in variable_counts.items() if count > 1),
        step_names=step_names,
        ambiguous_step_names=frozenset(key for key, count in step_counts.items() if count > 1),
    )
    issues.extend(resolve_function_block_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        member_paths=member_paths,
    ))
    for issue in issues:
        routines = (controller.add_on_instructions[issue.program_name].routines
                    if issue.scope == "function_block" else controller.programs[issue.program_name].routines)
        obj = routines[issue.routine_name].graphical_diagrams[
            issue.diagram_index].objects[issue.object_index]
        target = obj.pins[issue.pin_index] if issue.pin_index is not None else obj
        # Snapshot provenance is shared with the source capture, including
        # ordinal member identity. Do not invent a source location from names.
        metadata = target.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            issue.code, f"{issue.program_name}/{issue.routine_name}: {issue.expression!r}",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    # Shared symbols can expose ambiguity, but cannot establish vendor order.
    # Preserve separately evidenced ordering and diagnose unresolved networks.
    flagged_locations = {d.source for d in result.diagnostics if d.code != "unresolved_graphical_connections"}
    excluded_diagrams = frozenset(
        (program.name, routine.name, diagram_index)
        for program in controller.programs.values()
        for routine in program.routines.values()
        for diagram_index, diagram in enumerate(routine.graphical_diagrams)
        if diagram.source_extensions and _location(diagram.source_extensions[0]) in flagged_locations
    )
    function_block_excluded_diagrams = frozenset(
        (aoi.name, routine.name, diagram_index)
        for aoi in controller.add_on_instructions.values()
        for routine in aoi.routines.values()
        for diagram_index, diagram in enumerate(routine.graphical_diagrams)
        if diagram.source_extensions and _location(diagram.source_extensions[0]) in flagged_locations
    )
    _EXECUTION_ORDER_MESSAGES = {
        "ambiguous_block_order": "shared variable appears on output pins of multiple blocks",
        "cyclic_block_dependency": "explicit links and overrides form a cycle; no valid execution order exists",
        "unresolved_execution_after": "execAfter does not name exactly one other block in the same network",
    }
    for issue in resolve_fbd_execution_order(
        controller, excluded=excluded_diagrams, function_block_excluded=function_block_excluded_diagrams,
    ):
        routines = (controller.add_on_instructions[issue.program_name].routines
                    if issue.scope == "function_block" else controller.programs[issue.program_name].routines)
        diagram = routines[issue.routine_name].graphical_diagrams[issue.diagram_index]
        metadata = diagram.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            issue.code, f"{issue.program_name}/{issue.routine_name}: {_EXECUTION_ORDER_MESSAGES[issue.code]}",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    for container_name, routine_name, diagram in [
        (program.name, routine.name, diagram)
        for program in controller.programs.values()
        for routine in program.routines.values()
        for diagram in routine.graphical_diagrams
    ] + [
        (aoi.name, routine.name, diagram)
        for aoi in controller.add_on_instructions.values()
        for routine in aoi.routines.values()
        for diagram in routine.graphical_diagrams
    ]:
        if diagram.language != "FBD" or diagram.execution_order_resolved:
            continue
        metadata = diagram.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            "unresolved_block_order",
            f"{container_name}/{routine_name}: block order needs link/override interpretation; "
            "task scheduling is a separate known property",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    for code, element in resolve_sequential_bindings(
        controller, interfaces=result.library_interfaces, identifier_pattern=EXPRESSION_SPEC.identifier,
        ambiguous_names=frozenset(key for key, count in variable_counts.items() if count > 1),
    ):
        metadata = element.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            code, f"SFC variable expression {element.text!r}: {element.binding_kind}",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    for issue in resolve_sfc_connectivity(controller):
        chart = controller.programs[issue.program_name].routines[issue.routine_name].sequential_charts[
            issue.chart_index]
        network_index, child_index = issue.element_path
        element = chart.elements[network_index].children[child_index]
        metadata = element.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            issue.code, f"{issue.program_name}/{issue.routine_name}: {issue.detail}",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    for code, item in match_library_calls(
        controller, result.library_interfaces, direction_aliases=spec.library_direction_aliases,
    ):
        metadata = item.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            code, f"Library signature match: {item.interface_status}; source call retained",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    return result


def parse_projects(artifact: CapturedArtifact, *, spec: MappingSpec = BASIC_MAPPING) -> list[ParsedProject]:
    """Map every supported exchange member independently in archive order.

    The caller must still inspect capture diagnostics on the input and members;
    an empty list does not imply a successfully parsed empty project.
    """
    projects = []
    if artifact.section is not None and artifact.section.tag in spec.roots:
        projects.append(parse_project(artifact, spec=spec))
    for member in artifact.members:
        projects.extend(parse_projects(member, spec=spec))
    return projects
