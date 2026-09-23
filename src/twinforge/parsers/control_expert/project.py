"""Conservative basic mapping from captured exchange sections to neutral objects."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re

from twinforge.model import (
    AddOnInstruction, AddOnInstructionParameter, Chassis, CompositeTagValue, CompositeTagValueNode,
    Controller, Datatype, DatatypeMember,
    Identity, Module, Program, Resource, Routine, SourceExtension, StructuredTextLine, Tag, TagValue, Task,
)
from twinforge.schema.control_expert.mapping import BASIC_MAPPING, MappingSpec, PathSpec
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC
from twinforge.schema.control_expert import device_ddt_catalog
from twinforge.analysis.execution_order import resolve_fbd_execution_order
from twinforge.analysis.graphical_bindings import (
    TagWriteEvidence, _unique_by_name, member_path_context, resolve_coil_write_evidence,
    resolve_function_block_bindings, resolve_graphical_bindings,
)
from twinforge.analysis.library_calls import match_library_calls
from twinforge.analysis.sequential_bindings import resolve_sequential_bindings
from twinforge.analysis.sfc_connectivity import resolve_sfc_connectivity
from twinforge.analysis.tag_dependencies import TagDependencyGraph, build_tag_dependency_graph

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
    coil_write_evidence: list[TagWriteEvidence] = field(default_factory=list)
    tag_dependency_graph: TagDependencyGraph | None = None

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


def _library_description(node: CapturedSection) -> str | None:
    # Schneider's own documentation text for a library block, e.g.
    # `<attribute name="TypeDescriptiveForm" value="  The function block is
    # used as the On delay...&#xA;">`, a direct child of EFSource/EFBSource/
    # FBSource alongside other name/value `attribute` pairs (IsTypeHidden,
    # TypeCodeCheckSumString, ...) this project does not otherwise interpret.
    # An empty value is real (most blocks have no descriptive text) but is
    # not documentation, so it is treated the same as absent.
    for attribute in _select(node, ("attribute",)):
        if attribute.raw_attributes.get("name") == "TypeDescriptiveForm":
            value = attribute.raw_attributes.get("value")
            return value if value else None
    return None


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
    known_datatypes: dict[str, Datatype], catalog_datatypes: dict[str, Datatype],
) -> None:
    _declare_variables(
        result, _select(root, spec.variables), spec, known_datatypes, catalog_datatypes, set(),
        result.controller.add_tag)


def _resources(
    result: ParsedProject, root: CapturedSection, spec: MappingSpec,
    known_datatypes: dict[str, Datatype], catalog_datatypes: dict[str, Datatype],
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

        _declare_variables(result, declarations, spec, known_datatypes, catalog_datatypes, set(), register)
        result.controller.add_resource(resource)


def _type_definition(
    base_type: str, known_datatypes: dict[str, Datatype], catalog_datatypes: dict[str, Datatype],
    result: ParsedProject,
) -> tuple[Datatype | None, "AddOnInstruction | None", LibraryInterface | None, Datatype | None]:
    """Classify a tag's declared type against every kind of definition this
    project captures -- a user-defined DDT, a captured Function Block (DFB)
    instance, or a library (EFB) block interface -- so unresolved_type is
    raised only when none of those, nor the vendor Device DDT catalog,
    actually apply. A DFB instance is checked before library interfaces:
    every DFB is also registered there (as a "user_function_block" kind, for
    call validation), and the richer AddOnInstruction definition should win
    over that duplicate registration. The catalog is checked last, after
    every kind of project evidence: it is vendor documentation, not
    something this project captured, kept in its own result slot
    (vendor_documented_type) precisely so it is never confused with one.
    """
    key = base_type.casefold()
    datatype = known_datatypes.get(key)
    if datatype is not None:
        return datatype, None, None, None
    function_block = result.controller.add_on_instructions.get(base_type)
    if function_block is None:
        for name, instance in result.controller.add_on_instructions.items():
            if name.casefold() == key:
                function_block = instance
                break
    if function_block is not None:
        return None, function_block, None, None
    # Unlike DDTs and DFB instances (both name-unique by construction via
    # _unique_name at declaration time), nothing prevents two library
    # interface registrations (EFBSource/EFSource/FBSource) from sharing a
    # name; picking the first would silently guess between them.
    interface_matches = [interface for interface in result.library_interfaces
                         if interface.name and interface.name.casefold() == key]
    if len(interface_matches) == 1:
        return None, None, interface_matches[0], None
    catalog_datatype = catalog_datatypes.get(key)
    if catalog_datatype is not None:
        return None, None, None, catalog_datatype
    return None, None, None, None


# Real corpus evidence only ever declares an initializer on these IEC scalar
# families; TIME (also evidenced) stays lexical-only -- no duration
# conversion factor is invented, matching how the L5X converter's own scalar
# promotion (converters/l5x/decorated_value.py) also leaves unmapped types
# unpromoted rather than guessing.
_PROMOTABLE_BOOL_TYPES = frozenset({"BOOL", "EBOOL"})
_PROMOTABLE_INTEGER_TYPES = frozenset({"INT", "UINT", "DINT", "UDINT", "BYTE", "WORD", "DWORD"})
_PROMOTABLE_REAL_TYPES = frozenset({"REAL", "LREAL"})


def _promote_initial_value(data_type: str, lexical_value: str) -> "TagValue | None":
    """Promote one Control Expert initializer literal to a typed value, or None.

    Only a shape this project already recognizes as a literal elsewhere
    (``EXPRESSION_SPEC.literals``) is attempted, so a malformed or
    unsupported initializer text is never guessed at -- it just stays
    lexical-only, the same outcome as an unpromotable type.
    """
    text = lexical_value.strip()
    normalized = data_type.strip().upper()
    if not any(re.fullmatch(pattern, text, re.IGNORECASE) for pattern in EXPRESSION_SPEC.literals):
        return None
    if normalized in _PROMOTABLE_BOOL_TYPES:
        if re.fullmatch("TRUE|FALSE", text, re.IGNORECASE):
            return TagValue(text.upper() == "TRUE", normalized, lexical_value, source_format="Lexical")
        # "0"/"1" is standard IEC 61131-3 BOOL literal syntax too (real corpus
        # evidence: Sim_BBA01_PFe="0", Sim_BBB01_PFe="1"), distinct from a
        # numeric type's own integer literal below.
        if text in {"0", "1"}:
            return TagValue(text == "1", normalized, lexical_value, source_format="Lexical")
    if normalized in _PROMOTABLE_INTEGER_TYPES:
        based = re.fullmatch(r"(2|8|16)#([0-9A-Fa-f_]+)", text)
        if based:
            base, digits = based.groups()
            return TagValue(int(digits.replace("_", ""), int(base)), normalized, lexical_value,
                            radix=f"{base}#", source_format="Lexical")
        if re.fullmatch(r"[+-]?[0-9]+", text):
            return TagValue(int(text), normalized, lexical_value, source_format="Lexical")
        return None
    if normalized in _PROMOTABLE_REAL_TYPES:
        if re.fullmatch(r"[+-]?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)(?:[Ee][+-]?[0-9]+)?", text):
            return TagValue(float(text), normalized, lexical_value, source_format="Lexical")
        return None
    return None


def _composite_value_node(
    node: CapturedSection, container: "Datatype | AddOnInstruction | None", own_type_name: str | None,
    known_datatypes: dict[str, Datatype], catalog_datatypes: dict[str, Datatype], array_pattern: str,
) -> CompositeTagValueNode:
    """Recursively resolve one `instanceElementDesc` (struct member, DFB
    instance local-variable override, or array element -- one generic source
    element covers all three, distinguished by whether its name is an "[N]"
    array index) against its declaring type, and promote a scalar leaf value
    the same conservative way a top-level tag's own initializer already is.

    `container` is the enclosing composite type this node's own name is
    looked up in: a `Datatype` for a struct member, an `AddOnInstruction` for
    a DFB instance's local-variable override -- real evidence, not a
    parameter override: `IO_READAPI`'s `IO_READVAR` local is itself an
    `IO_READVAR` instance, resolved the same way one level deeper.
    `own_type_name` is the *parent* node's own resolved (already
    array-unwrapped) element type, used only by an array-index child, which
    reuses its declaring array's element type rather than being looked up by
    name.
    """
    raw_name = node.raw_attributes.get("name", "")
    index_match = re.fullmatch(r"\[(\d+)\]", raw_name)
    value_node = next((child for child in node.ordered_children if child.tag == "value"), None)
    lexical_value = value_node.text if value_node is not None else None

    member_definition: DatatypeMember | None = None
    local_variable_definition: Tag | None = None
    resolved_type_name: str | None = None
    if index_match:
        resolved_type_name = own_type_name
    elif isinstance(container, Datatype):
        member_definition = next(
            (m for m in container.members if m.name.casefold() == raw_name.casefold()), None)
        if member_definition is not None:
            resolved_type_name = member_definition.data_type_name
    elif isinstance(container, AddOnInstruction):
        local_variable_definition = next(
            (t for t in container.local_tags.values() if t.name.casefold() == raw_name.casefold()), None)
        if local_variable_definition is not None:
            resolved_type_name = local_variable_definition.data_type

    # A project DDT member's own data_type_name already arrives pre-stripped
    # of any array wrapper (see _datatypes), but a DFB local variable's raw
    # typeName and the vendor Device DDT catalog's own data_type_name do not
    # -- real evidence: T_U_DIS_SIS_IN_16's own CH_IN_A member is
    # "ARRAY[0..7] OF T_U_DIS_SIS_CH_IN". Element-type propagation (both for
    # this node's own leaf promotion and for what its index children look up
    # against) always uses the unwrapped form, mirroring the same
    # normalization _declare_variables already applies to a top-level tag.
    element_type_name = resolved_type_name
    if resolved_type_name:
        array_match = re.fullmatch(array_pattern, resolved_type_name, flags=re.IGNORECASE)
        if array_match:
            element_type_name = array_match[3]

    child_container: Datatype | AddOnInstruction | None = None
    if member_definition is not None:
        child_container = member_definition.data_type
    elif local_variable_definition is not None:
        child_container = (local_variable_definition.function_block_instance
                           or local_variable_definition.data_type_definition
                           or local_variable_definition.vendor_documented_type)
    if child_container is None and element_type_name:
        key = element_type_name.casefold()
        child_container = known_datatypes.get(key) or catalog_datatypes.get(key)

    children = tuple(
        _composite_value_node(child, child_container, element_type_name, known_datatypes, catalog_datatypes,
                              array_pattern)
        for child in node.ordered_children if child.tag == "instanceElementDesc")

    value = None
    radix = None
    if not children and element_type_name and lexical_value is not None:
        promoted = _promote_initial_value(element_type_name, lexical_value)
        if promoted is not None:
            value, radix = promoted.value, promoted.radix

    return CompositeTagValueNode(
        source_kind="instanceElementDesc",
        name=None if index_match else (raw_name or None),
        index=index_match.group(1) if index_match else None,
        data_type=resolved_type_name,
        radix=radix,
        lexical_value=lexical_value,
        value=value,
        member_definition=member_definition,
        local_variable_definition=local_variable_definition,
        data_type_definition=child_container if isinstance(child_container, Datatype) else None,
        children=children,
        raw_attributes=dict(node.raw_attributes),
    )


def _composite_fully_resolved(node: CompositeTagValueNode) -> bool:
    """Whether every leaf under this node promoted and every intermediate
    node's own member/local-variable identity was resolved -- mirrors the
    scalar initializer's own "nothing left uninterpreted" standard.
    """
    if node.source_kind != "variables" and node.data_type is None:
        return False
    if node.children:
        return all(_composite_fully_resolved(child) for child in node.children)
    return node.lexical_value is None or node.value is not None


def _declare_variables(
    result: ParsedProject, nodes: list[CapturedSection], spec: MappingSpec,
    known_datatypes: dict[str, Datatype], catalog_datatypes: dict[str, Datatype],
    used: set[str], register,
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

        # Type resolution happens up front (still reported in its original
        # relative order below) so composite initial value resolution, which
        # needs to know the tag's own resolved type, can use it.
        match = re.fullmatch(spec.array_pattern, type_name or "", flags=re.IGNORECASE)
        base_type = type_name
        array_bounds_valid = True
        if match:
            lower, upper = int(match[1]), int(match[2])
            base_type = match[3]
            array_bounds_valid = upper >= lower
            if array_bounds_valid:
                tag.metadata["source_array_bounds"] = [[lower, upper]]
                tag.metadata["source_array_element_type"] = base_type
        if base_type:
            (tag.data_type_definition, tag.function_block_instance, tag.library_type,
             tag.vendor_documented_type) = _type_definition(base_type, known_datatypes, catalog_datatypes, result)
        known = (tag.data_type_definition or tag.function_block_instance or tag.library_type
                or tag.vendor_documented_type)

        initializers = _select(node, spec.initializers)
        if initializers:
            tag.metadata["source_initial_values"] = [dict(n.raw_attributes) for n in initializers]
            if len(initializers) == 1:
                value_text = initializers[0].raw_attributes.get("value")
                if value_text is not None:
                    tag.initial_value = _promote_initial_value(type_name or "", value_text)
            if tag.initial_value is None:
                result.report("uninterpreted_initial_value", f"{name}: initializer retained lexically", node)
        instance_elements = _select(node, spec.instance_elements)
        if instance_elements:
            container = tag.function_block_instance or tag.data_type_definition or tag.vendor_documented_type
            root = CompositeTagValueNode(
                source_kind="variables", name=name, data_type=type_name,
                children=tuple(
                    _composite_value_node(child, container, base_type, known_datatypes, catalog_datatypes,
                                          spec.array_pattern)
                    for child in instance_elements),
            )
            tag.composite_initial_value = CompositeTagValue(
                root=root, data_type_definition=tag.data_type_definition or tag.vendor_documented_type)
            if not _composite_fully_resolved(root):
                result.report(
                    "uninterpreted_composite_initial_value",
                    f"{name}: composite/array initial value retained lexically", node)
        if match:
            if not array_bounds_valid:
                result.report("invalid_array_bounds", f"{name}: upper bound precedes lower bound", node)
            # The model has no typed lower-bound field. Do not normalize this
            # into a zero-based dimensions string and imply portability.
            result.report("unresolved_array_type", f"{name}: array expression and bounds retained; type not resolved", node)
        if known is None and (not base_type or base_type.upper() not in spec.scalar_types):
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
    known_datatypes: dict[str, Datatype], catalog_datatypes: dict[str, Datatype],
) -> None:
    """Map user-defined Function Block (DFB) definitions: interface, locals and body.

    A crypted body is genuinely opaque; only the interface is retained. Body
    bindings (pin/symbol resolution) are not attempted here -- an FB body's
    parameters and locals form their own namespace, not the project's global
    tags, and the existing binding analyses assume one flat global scope.

    Two passes: every DFB is registered by name first, then interfaces/locals/
    bodies are filled in -- a local variable typed as *another* DFB (real
    evidence: `IO_READAPI`'s `IO_READVAR` local is itself an `IO_READVAR`
    instance) must be able to resolve regardless of which DFB is declared
    first in source order, the same forward-reference problem DDT members
    already solve with their own two-pass capture.
    """
    used: set[str] = set()
    pending: list[tuple[CapturedSection, AddOnInstruction]] = []
    for node in _select(root, spec.function_blocks):
        name = _unique_name(result, node, node.raw_attributes.get(spec.function_block_name_attribute), used, "function block")
        if name is None:
            continue
        comment = _first(node, spec.comments)
        aoi = AddOnInstruction(name=name, description=comment.text if comment else None,
                               source_extensions=[_extension(node)])
        result.controller.add_add_on_instruction(aoi)
        pending.append((node, aoi))
    for node, aoi in pending:
        name = aoi.name
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
                local_tag = Tag(name=lname, data_type=type_name, source_extensions=[_extension(local_node)])
                # Mirrors _declare_variables: an array-wrapped type resolves
                # its element type, never the wrapper text itself -- real
                # evidence here (e.g. "_adelay: ARRAY[0..15] OF INT") is
                # otherwise a plain scalar element, wrongly unresolved_type.
                array_match = re.fullmatch(spec.array_pattern, type_name or "", flags=re.IGNORECASE)
                base_type = type_name
                if array_match:
                    lower, upper = int(array_match[1]), int(array_match[2])
                    base_type = array_match[3]
                    if upper >= lower:
                        local_tag.metadata["source_array_bounds"] = [[lower, upper]]
                        local_tag.metadata["source_array_element_type"] = base_type
                    else:
                        result.report("invalid_array_bounds", f"{name}.{lname}: upper bound precedes lower bound",
                                      local_node)
                    result.report("unresolved_array_type",
                                  f"{name}.{lname}: array expression and bounds retained; type not resolved",
                                  local_node)
                if base_type:
                    (local_tag.data_type_definition, local_tag.function_block_instance,
                     local_tag.library_type, local_tag.vendor_documented_type) = _type_definition(
                        base_type, known_datatypes, catalog_datatypes, result)
                local_known = (local_tag.data_type_definition or local_tag.function_block_instance
                              or local_tag.library_type or local_tag.vendor_documented_type)
                if local_known is None and (not base_type or base_type.upper() not in spec.scalar_types):
                    result.report("unresolved_type",
                                  f"{name}.{lname}: no supported type definition for {base_type!r}", local_node)
                local_tag.metadata["visibility"] = visibility
                aoi.add_local_tag(local_tag)
        programs = _select(node, spec.function_block_program)
        crypted = _first(node, spec.function_block_crypted)
        if crypted is not None:
            # The body itself is genuinely opaque (Schneider's own encryption,
            # not this project's to break); characterized, not decoded. The
            # full hex blob is already retained verbatim at the capture layer
            # (source_extensions), so only size/encoding/identity evidence --
            # small enough to appear safely in an inspection report -- is
            # copied onto the neutral model.
            hex_text = crypted.text or ""
            aoi.metadata["encrypted_body"] = {
                "encoding": crypted.raw_attributes.get("Encoding"),
                "hex_length": len(hex_text),
                "sha256": hashlib.sha256(hex_text.encode("ascii", errors="ignore")).hexdigest(),
            }
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
        task.metadata["source_task_attributes"] = dict(attrs)
        # Milliseconds: inferred, not from a published XEF schema for these
        # exact attributes, but from a real tool's live COM automation
        # against Control Expert 14.0 (apexsotjo-blip/control-expert-mcp),
        # whose own task.Periodicity/task.WatchDog properties -- the same
        # underlying task settings -- are handled in milliseconds there
        # (its own parameters are literally named periodicity_ms/watchdog_ms).
        # "0" for a cyclic task's valueType is not a period; only a periodic
        # task's own value is promoted.
        watchdog_text = attrs.get("maxExecTime")
        if watchdog_text is not None and re.fullmatch(r"[0-9]+", watchdog_text):
            task.watchdog = int(watchdog_text)
        if task.task_type == "periodic":
            rate_text = attrs.get("valueType")
            if rate_text is not None and re.fullmatch(r"[1-9][0-9]*", rate_text):
                task.rate = int(rate_text)
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
                description=_library_description(node),
                source_extensions=[_extension(node)],
            ))
    known_datatypes = _datatypes(result, root, spec)
    # Built once and shared across every tag: distinct Datatype instances per
    # tag would break identity comparisons two tags of the same catalog type
    # should share, unlike known_datatypes/add_on_instructions/
    # library_interfaces, which already are singletons by construction.
    catalog_datatypes = device_ddt_catalog.datatypes()
    # Function Blocks are captured before variables/resources so a tag typed
    # as a DFB instance can be cross-referenced immediately, the same as one
    # typed as a DDT; _function_blocks does not itself depend on tags or
    # resources having been captured first.
    _function_blocks(result, root, spec, known_datatypes, catalog_datatypes)
    _variables(result, root, spec, known_datatypes, catalog_datatypes)
    _resources(result, root, spec, known_datatypes, catalog_datatypes)
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
    # Programs are already casefold-unique by construction (_unique_name at
    # declaration time), so no ambiguity is possible here in practice; still
    # threaded through for symmetry with steps/symbols, which are not.
    program_names = {p.name.casefold(): p.name for p in controller.programs.values()}
    # A call's own type_name (e.g. "INITCHART") must map to exactly one
    # interface to know its parameter types reliably -- reusing the same
    # ambiguity handling library_interfaces lookups already apply elsewhere.
    call_parameter_types = {
        name: {p.name.casefold(): p.data_type for p in interface.parameters if p.name and p.data_type}
        for name, interface in _unique_by_name(result.library_interfaces).items()
    }
    issues = resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, member_paths=member_paths,
        literal_patterns=EXPRESSION_SPEC.literals,
        ambiguous_names=frozenset(key for key, count in variable_counts.items() if count > 1),
        step_names=step_names,
        ambiguous_step_names=frozenset(key for key, count in step_counts.items() if count > 1),
        program_names=program_names, call_parameter_types=call_parameter_types,
        direct_address_pattern=EXPRESSION_SPEC.direct_address,
    )
    issues.extend(resolve_function_block_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        member_paths=member_paths, direct_address_pattern=EXPRESSION_SPEC.direct_address,
        program_names=program_names, call_parameter_types=call_parameter_types,
        step_names=step_names,
        ambiguous_step_names=frozenset(key for key, count in step_counts.items() if count > 1),
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
    # Coil write evidence needs target_tag already resolved by the bindings
    # pass above; every tag with a coil write is retained, not only the
    # multiple-writer ones, matching how shared_variables exposes full
    # evidence rather than only its own ambiguous cases.
    result.coil_write_evidence = resolve_coil_write_evidence(controller)
    for evidence in result.coil_write_evidence:
        if len(evidence.locations) < 2:
            continue
        last = evidence.locations[-1]
        obj = (controller.programs[last.program_name].routines[last.routine_name]
               .graphical_diagrams[last.diagram_index].objects[last.object_index])
        metadata = obj.source_extensions[0].metadata
        writers = "; ".join(f"{loc.program_name}/{loc.routine_name}" for loc in evidence.locations)
        result.diagnostics.append(Diagnostic(
            "multiple_coil_writers", f"{evidence.tag_name}: written by coils in {writers}",
            SourceLocation(metadata["input_sha256"], metadata["members"], metadata["xml_path"]),
        ))
    # Reuses the project-wide step registry already built above for LD
    # contact/chart-control-call resolution -- the identical evidence
    # standard, now also covering a ".X" reference inside an ST expression
    # (e.g. "IF G1_0.X THEN"), which the graphical-binding passes above
    # never see since they only walk graphical diagrams, not ST bodies.
    result.tag_dependency_graph = build_tag_dependency_graph(
        controller, step_names=step_names,
        ambiguous_step_names=frozenset(key for key, count in step_counts.items() if count > 1),
    )
    for ambiguous in result.tag_dependency_graph.ambiguous_step_state_references:
        routine = controller.programs[ambiguous.program_name].routines[ambiguous.routine_name]
        metadata = routine.source_extensions[0].metadata
        result.diagnostics.append(Diagnostic(
            "ambiguous_step_state_reference",
            f"{ambiguous.program_name}/{ambiguous.routine_name}: {ambiguous.operand!r} "
            f"names more than one declared step",
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
        controller, identifier_pattern=EXPRESSION_SPEC.identifier,
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
