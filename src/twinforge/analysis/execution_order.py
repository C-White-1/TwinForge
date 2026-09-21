"""Resolve FBD block execution order from explicit links, or diagnose why not.

Grounded in Schneider's own documented rule (se.com FAQ FA340273): blocks with
no other block as an input execute first, in grid position order; blocks that
do have one execute after, also in position order -- dependency overrides
position when they conflict. That rule is worded for one dependency level;
resolving it here as a full topological sort (position as the tie-break at
each level) is the mathematically necessary generalization for deeper chains,
not a separately vendor-confirmed rule -- real chains up to 7 levels deep
exist in the corpus, so this is not a theoretical concern. Shared symbol
occurrences alone still do not establish wires, memory effects or order --
only an explicit, fully-resolved `linkFB` graph does.

A block's `execAfter` override is read as one extra dependency edge onto the
block it names. Schneider's FAQ FA332812 confirms a block property can force
execution order but does not document the mechanism or value grammar, so this
is an inference from the attribute's name plus its one real corpus occurrence
(an instance name in the same network), and is labelled as such in the basis.
"""
from dataclasses import dataclass

from twinforge.model import Controller
from twinforge.model.graphical import GraphicalDiagram

_UNRESOLVED_BINDING_KINDS = frozenset({
    "unresolved_expression", "missing_symbol", "ambiguous_symbol", "invalid_output_literal",
})


@dataclass(frozen=True)
class ExecutionOrderIssue:
    # The enclosing Program or, when scope == "function_block", AddOnInstruction.
    program_name: str
    routine_name: str
    diagram_index: int
    code: str
    scope: str = "program"


def _dependency_graph(diagram: GraphicalDiagram, block_indices: set[int]) -> dict[int, set[int]] | None:
    """Return {block: {blocks it depends on}}, or None if any link is untrustworthy."""
    deps: dict[int, set[int]] = {i: set() for i in block_indices}
    for link in diagram.links:
        if link.source.status != "resolved" or link.destination.status != "resolved":
            # An unresolved link could, had it resolved, have connected two
            # blocks this diagram's own dependency graph would then be
            # missing. Do not claim a complete graph despite the gap.
            return None
        source, destination = link.source.object_index, link.destination.object_index
        if source in block_indices and destination in block_indices:
            deps[destination].add(source)
    # A shared symbol on one block's output pin and another's input pin is
    # real dataflow evidence this project has already proven is not always
    # backed by an explicit wire (the withdrawn shared_variable_dataflow
    # basis). Any such pair not also covered by a resolved link means the
    # graph above is incomplete, not merely conservative.
    for group in diagram.shared_variables:
        outputs = {i for i, _ in group.output_pins if i in block_indices}
        inputs = {i for i, _ in group.input_pins if i in block_indices}
        for source in outputs:
            for destination in inputs:
                if source != destination and source not in deps[destination]:
                    return None
    return deps


def _execution_overrides(diagram: GraphicalDiagram, blocks: list[int]) -> list[tuple[int, int]] | None:
    """(block, block it must follow) per `execAfter`, or None if any cannot be resolved."""
    by_name: dict[str, list[int]] = {}
    for i in blocks:
        name = diagram.objects[i].instance_name
        if name:
            by_name.setdefault(name.casefold(), []).append(i)
    overrides: list[tuple[int, int]] = []
    for i in blocks:
        target = (diagram.objects[i].execution_after or "").strip()
        if not target:
            continue
        matches = by_name.get(target.casefold(), [])
        if len(matches) != 1 or matches[0] == i:
            return None
        overrides.append((i, matches[0]))
    return overrides


def _topological_order(deps: dict[int, set[int]], position_key) -> list[int] | None:
    """Kahn's algorithm, releasing each wave in position order. None on a cycle."""
    remaining = {i: set(d) for i, d in deps.items()}
    order: list[int] = []
    while remaining:
        ready = sorted((i for i, unmet in remaining.items() if not unmet), key=position_key)
        if not ready:
            return None
        order.extend(ready)
        for i in ready:
            del remaining[i]
        for unmet in remaining.values():
            unmet.difference_update(ready)
    return order


def _resolve_routine_diagrams(
    diagrams: list[GraphicalDiagram], container_name: str, routine_name: str, scope: str,
    excluded: frozenset[tuple[str, str, str, int]],
) -> list[ExecutionOrderIssue]:
    issues: list[ExecutionOrderIssue] = []
    for diagram_index, diagram in enumerate(diagrams):
        # Clear obsolete results even when this run excludes the network.
        if diagram.execution_order_basis == "shared_variable_dataflow":
            diagram.execution_order.clear()
            diagram.execution_order_resolved = False
            diagram.execution_order_basis = None
        if diagram.execution_order_resolved or diagram.language != "FBD":
            continue
        if (scope, container_name, routine_name, diagram_index) in excluded:
            continue
        blocks = [i for i, obj in enumerate(diagram.objects) if obj.kind == "block"]
        if len(blocks) < 2:
            continue
        if any(obj.kind not in {"block", "annotation"} for obj in diagram.objects):
            continue
        block_indices = set(blocks)
        overrides = _execution_overrides(diagram, blocks)
        if overrides is None:
            issues.append(ExecutionOrderIssue(
                container_name, routine_name, diagram_index, "unresolved_execution_after", scope))
            continue
        # A pin failing to resolve to a *symbol* (a complex expression, or a
        # name outside this pass's scope) says nothing about whether an
        # explicit block-to-block wire is trustworthy, so it does not gate
        # order resolution below. It still gates the shared-variable
        # ambiguity check: a write conflict is only meaningful evidence when
        # the diagram's pins are otherwise clean.
        bad_pins = any(pin.binding_kind in _UNRESOLVED_BINDING_KINDS
                        for i in blocks for pin in diagram.objects[i].pins)
        if not bad_pins:
            ambiguous = False
            for group in diagram.shared_variables:
                outputs = {index for index, _ in group.output_pins if index in block_indices}
                if len(outputs) > 1:
                    issues.append(ExecutionOrderIssue(
                        container_name, routine_name, diagram_index, "ambiguous_block_order", scope))
                    ambiguous = True
                    break
            if ambiguous:
                continue
        deps = _dependency_graph(diagram, block_indices)
        if deps is None or any(diagram.objects[i].position is None for i in blocks):
            continue

        def position_key(index: int, diagram: GraphicalDiagram = diagram) -> tuple[int, int]:
            position = diagram.objects[index].position
            assert position is not None
            return (position.row, position.column)

        for destination, source in overrides:
            deps[destination].add(source)
        order = _topological_order(deps, position_key)
        if order is None:
            issues.append(ExecutionOrderIssue(
                container_name, routine_name, diagram_index, "cyclic_block_dependency", scope))
            continue
        diagram.execution_order = order
        diagram.execution_order_resolved = True
        diagram.execution_order_basis = (
            "dependency_order_with_exec_after" if overrides else "documented_dependency_order")
    return issues


def resolve_fbd_execution_order(
    controller: Controller, *, excluded: frozenset[tuple[str, str, int]] = frozenset(),
    function_block_excluded: frozenset[tuple[str, str, int]] = frozenset(),
) -> list[ExecutionOrderIssue]:
    issues: list[ExecutionOrderIssue] = []
    excluded_keyed = frozenset({("program", *key) for key in excluded} | {
        ("function_block", *key) for key in function_block_excluded})
    for program in controller.programs.values():
        for routine in program.routines.values():
            issues.extend(_resolve_routine_diagrams(
                routine.graphical_diagrams, program.name, routine.name, "program", excluded_keyed))
    for aoi in controller.add_on_instructions.values():
        for routine in aoi.routines.values():
            issues.extend(_resolve_routine_diagrams(
                routine.graphical_diagrams, aoi.name, routine.name, "function_block", excluded_keyed))
    return issues
