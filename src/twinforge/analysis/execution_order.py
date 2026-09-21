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
"""
from dataclasses import dataclass

from twinforge.model import Controller
from twinforge.model.graphical import GraphicalDiagram

_UNRESOLVED_BINDING_KINDS = frozenset({
    "unresolved_expression", "missing_symbol", "ambiguous_symbol", "invalid_output_literal",
})


@dataclass(frozen=True)
class ExecutionOrderIssue:
    program_name: str
    routine_name: str
    diagram_index: int
    code: str


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


def resolve_fbd_execution_order(
    controller: Controller, *, excluded: frozenset[tuple[str, str, int]] = frozenset(),
) -> list[ExecutionOrderIssue]:
    issues: list[ExecutionOrderIssue] = []
    for program in controller.programs.values():
        for routine in program.routines.values():
            for diagram_index, diagram in enumerate(routine.graphical_diagrams):
                # Clear obsolete results even when this run excludes the network.
                if diagram.execution_order_basis == "shared_variable_dataflow":
                    diagram.execution_order.clear()
                    diagram.execution_order_resolved = False
                    diagram.execution_order_basis = None
                if diagram.execution_order_resolved or diagram.language != "FBD":
                    continue
                if (program.name, routine.name, diagram_index) in excluded:
                    continue
                blocks = [i for i, obj in enumerate(diagram.objects) if obj.kind == "block"]
                if len(blocks) < 2:
                    continue
                if any(obj.kind not in {"block", "annotation"} for obj in diagram.objects):
                    continue
                if any(diagram.objects[i].execution_after for i in blocks):
                    continue
                block_indices = set(blocks)
                # A pin failing to resolve to a *symbol* (a complex expression,
                # or a name outside this pass's scope) says nothing about
                # whether an explicit block-to-block wire is trustworthy, so
                # it does not gate order resolution below. It still gates the
                # shared-variable ambiguity check: a write conflict is only
                # meaningful evidence when the diagram's pins are otherwise clean.
                bad_pins = any(pin.binding_kind in _UNRESOLVED_BINDING_KINDS
                                for i in blocks for pin in diagram.objects[i].pins)
                if not bad_pins:
                    ambiguous = False
                    for group in diagram.shared_variables:
                        outputs = {index for index, _ in group.output_pins if index in block_indices}
                        if len(outputs) > 1:
                            issues.append(ExecutionOrderIssue(
                                program.name, routine.name, diagram_index, "ambiguous_block_order"))
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

                order = _topological_order(deps, position_key)
                if order is None:
                    issues.append(ExecutionOrderIssue(
                        program.name, routine.name, diagram_index, "cyclic_block_dependency"))
                    continue
                diagram.execution_order = order
                diagram.execution_order_resolved = True
                diagram.execution_order_basis = "documented_dependency_order"
    return issues
