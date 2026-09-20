"""Order multi-block FBD networks from confirmed shared-variable data flow only.

No link/connector grammar is assumed: connectivity comes exclusively from
``diagram.shared_variables`` groups already produced by pin-expression
binding (twinforge.analysis.graphical_bindings). A network stays unresolved
whenever any relevant pin failed to bind cleanly, any block carries an
execution override, a shared variable has more than one writer, the
resulting dependency graph has a cycle, or the caller excludes it because of
an unrelated interpretation gap.
"""
from dataclasses import dataclass

from twinforge.model import Controller

_UNRESOLVED_BINDING_KINDS = frozenset({
    "unresolved_expression", "missing_symbol", "ambiguous_symbol", "invalid_output_literal",
})


@dataclass(frozen=True)
class ExecutionOrderIssue:
    program_name: str
    routine_name: str
    diagram_index: int
    code: str


def resolve_fbd_execution_order(
    controller: Controller, *, excluded: frozenset[tuple[str, str, int]] = frozenset(),
) -> list[ExecutionOrderIssue]:
    issues: list[ExecutionOrderIssue] = []
    for program in controller.programs.values():
        for routine in program.routines.values():
            for diagram_index, diagram in enumerate(routine.graphical_diagrams):
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
                if any(pin.binding_kind in _UNRESOLVED_BINDING_KINDS
                       for i in blocks for pin in diagram.objects[i].pins):
                    continue
                edges: dict[int, set[int]] = {i: set() for i in blocks}
                ambiguous = False
                for group in diagram.shared_variables:
                    writers = {index for index, _ in group.output_pins if index in edges}
                    if len(writers) > 1:
                        ambiguous = True
                        break
                    if not writers:
                        continue
                    writer = next(iter(writers))
                    readers = {index for index, _ in group.input_pins if index in edges}
                    for reader in readers:
                        if reader != writer:
                            edges[writer].add(reader)
                if ambiguous:
                    issues.append(ExecutionOrderIssue(
                        program.name, routine.name, diagram_index, "ambiguous_block_order"))
                    continue
                order, cyclic = _topological_order(blocks, edges)
                if cyclic:
                    # A genuine cycle is left to the generic unresolved-order
                    # diagnostic; the caller has no additional evidence to report.
                    continue
                diagram.execution_order = order
                diagram.execution_order_resolved = True
                diagram.execution_order_basis = "shared_variable_dataflow"
    return issues


def _topological_order(nodes: list[int], edges: dict[int, set[int]]) -> tuple[list[int], bool]:
    order: list[int] = []
    visiting: set[int] = set()
    visited: set[int] = set()
    cyclic = False

    def visit(node: int) -> None:
        nonlocal cyclic
        if cyclic or node in visited:
            return
        if node in visiting:
            cyclic = True
            return
        visiting.add(node)
        for target in sorted(edges[node]):
            visit(target)
        visiting.discard(node)
        visited.add(node)
        order.append(node)

    for node in nodes:
        visit(node)
        if cyclic:
            return [], True
    order.reverse()
    return order, False
