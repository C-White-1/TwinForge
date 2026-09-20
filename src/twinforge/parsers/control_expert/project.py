"""Conservative basic mapping from captured exchange sections to neutral objects."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from twinforge.model import (
    Chassis, Controller, Identity, Module, Program, Routine,
    SourceExtension, StructuredTextLine, Tag, Task,
)
from twinforge.schema.control_expert.mapping import BASIC_MAPPING, MappingSpec, PathSpec
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC
from twinforge.analysis.execution_order import resolve_fbd_execution_order
from twinforge.analysis.graphical_bindings import resolve_graphical_bindings
from twinforge.analysis.library_calls import match_library_calls
from twinforge.analysis.sequential_bindings import resolve_sequential_bindings
from twinforge.analysis.sfc_connectivity import resolve_sfc_connectivity

from twinforge.model.library_interface import LibraryInterface, LibraryParameter
from twinforge.model.sequential import SequentialElement

from .capture import CapturedArtifact, CapturedSection, Diagnostic, SourceLocation
from .graphical import parse_diagrams
from .ladder import parse_ladder_rungs
from .sfc import parse_charts
from .evidence import source_extension as _extension


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


def _variables(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    used: set[str] = set()
    for node in _select(root, spec.variables):
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
        if not base_type or base_type.upper() not in spec.scalar_types:
            result.report("unresolved_type", f"{name}: no supported type definition for {base_type!r}", node)
        result.controller.add_tag(tag)


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
            program.add_routine(routine)
        else:
            result.report("ambiguous_language", f"{name}: expected one supported source body, found {len(sources)}", node)
        result.controller.add_program(program)
        identities[name.casefold()] = (attrs.get("task"), node)

    task_nodes = _select(root, spec.tasks)
    task_counts: dict[str, int] = {}
    for node in task_nodes:
        key = node.raw_attributes.get("task", "").casefold()
        task_counts[key] = task_counts.get(key, 0) + 1
    used = set()
    programs = {name.casefold(): program for name, program in result.controller.programs.items()}
    scheduled: set[str] = set()
    for node in task_nodes:
        attrs = node.raw_attributes
        name = _unique_name(result, node, attrs.get("task"), used, "task")
        if name is None:
            continue
        task = Task(name=name, task_type=attrs.get("taskType"), source_extensions=[_extension(node)])
        # Do not assign rate/watchdog units from undocumented raw values.
        task.metadata["source_task_attributes"] = dict(attrs)
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
            for routine in programs[key].routines.values():
                routine.metadata.setdefault("task_schedule", []).append({
                    "task_name": name,
                    "task_type": task.task_type,
                    "section_index": section_index,
                    "eligibility": "each_active_task_cycle" if task.task_type == "cyclic" else "task_dependent",
                    "execution_conditions": "not_evaluated",
                })
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
    _variables(result, root, spec)
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
    issues = resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier,
        literal_patterns=EXPRESSION_SPEC.literals,
        ambiguous_names=frozenset(key for key, count in variable_counts.items() if count > 1),
        step_names=step_names,
        ambiguous_step_names=frozenset(key for key, count in step_counts.items() if count > 1),
    )
    for issue in issues:
        obj = controller.programs[issue.program_name].routines[issue.routine_name].graphical_diagrams[
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
    for issue in resolve_fbd_execution_order(controller, excluded=excluded_diagrams):
        diagram = controller.programs[issue.program_name].routines[issue.routine_name].graphical_diagrams[
            issue.diagram_index]
        metadata = diagram.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            issue.code, f"{issue.program_name}/{issue.routine_name}: shared variable appears on output pins of multiple blocks",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    for program in controller.programs.values():
        for routine in program.routines.values():
            for diagram in routine.graphical_diagrams:
                if diagram.execution_order_resolved:
                    continue
                metadata = diagram.source_extensions[0].metadata
                result.diagnostics.append(Diagnostic(
                    "unresolved_block_order",
                    f"{program.name}/{routine.name}: block order needs link/override interpretation; "
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
