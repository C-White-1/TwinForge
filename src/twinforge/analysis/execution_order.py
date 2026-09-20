"""Diagnose shared-variable ambiguity without inferring vendor execution order.

Shared symbol occurrences are preserved on the diagram. They do not establish
wires, memory effects or a same-scan ordering rule, even for a unique chain.
Only a separately evidenced ordering rule may mark execution order resolved.
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
                if any(pin.binding_kind in _UNRESOLVED_BINDING_KINDS
                       for i in blocks for pin in diagram.objects[i].pins):
                    continue
                block_indices = set(blocks)
                for group in diagram.shared_variables:
                    outputs = {index for index, _ in group.output_pins if index in block_indices}
                    if len(outputs) > 1:
                        issues.append(ExecutionOrderIssue(
                            program.name, routine.name, diagram_index, "ambiguous_block_order"))
                        break
    return issues
