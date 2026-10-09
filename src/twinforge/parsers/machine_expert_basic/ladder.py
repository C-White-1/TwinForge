"""Build a rung's `LadderSeries` network from its `.smbp` grid cells.

Milestone 2 of docs/roadmaps/machine-expert-basic-roadmap.md. The grid rules
come from `schema/machine_expert_basic/ladder.py` and were verified against
each rung's Instruction List (docs/architecture/machine-expert-basic-smbp-format.md):

- Node `(row, k)` is the vertical edge before column `k`; every `(row, 0)`
  is the left rail.
- A cell at `(r, c)` of width `w` that has `Left` connects node `(r, c)` to
  node `(r, c + w)`. `Down`/`Up` join its right node to the row below/above.
- A block pin sits on a fixed row offset for its block type.

The grid becomes a directed graph whose vertices are joined nodes and whose
edges are cells. Each output becomes an edge into one virtual sink, so a
rung with several outputs is one two-terminal graph. Repeated series and
parallel reduction then turns it into one `LadderSeries`, the same shape
L5X and CCW rungs use: shared conditions first, then a `LadderParallel` of
output branches. A grid that does not reduce (a bridge) gets no network.

Function blocks follow the Control Expert convention: a block output used
as a condition is a `BLOCK_OUTPUT_REFERENCE` leaf (`%TM0.Q`), and each wired
input pin is its mirror, a `FUNCTION_BLOCK_INPUT` sink (`%TM0.IN`).
Every element without a portable `LadderOperation` stays in the network as
`UNSUPPORTED`, with its element type as `source_mnemonic`.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re

from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderPosition, LadderSeries
from twinforge.schema.machine_expert_basic.ladder import LADDER_SPEC, LadderSpec

from .expression import expression_instruction

Cell = dict[str, str]
_RAIL = ("rail",)
_SINK = ("sink",)


class NetworkUnresolved(Exception):
    """The grid cannot be turned into a network without guessing."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class _Edge:
    source: tuple
    target: tuple
    series: LadderSeries
    # (row, column) of the first cell in this edge; orders parallel branches
    # top to bottom, as drawn.
    order: tuple[int, int]


_MEMBER_READ = re.compile(r"(%[A-Z_]+\d+)\.([A-Za-z_]\w*)")


def declared_name(address: str | None, symbols: Mapping[str, str]) -> tuple[str | None, tuple[str, ...]]:
    """The declared symbol for an address, keeping the address as an annotation.

    A member read such as `%TM2.Q` uses its object's symbol (`DELAY.Q`). An
    address with no symbol is returned unchanged with no annotation.
    """
    if not address:
        return address, ()
    symbol = symbols.get(address)
    if symbol is None:
        member = _MEMBER_READ.fullmatch(address)
        if member is not None and member.group(1) in symbols:
            symbol = f"{symbols[member.group(1)]}.{member.group(2)}"
    return (symbol, (f"address={address}",)) if symbol else (address, ())


def _connections(cell: Cell, spec: LadderSpec) -> set[str]:
    return {part.strip() for part in cell.get(spec.connection, "").split(",")}


def _operand(cell: Cell, field_name: str | None) -> str | None:
    return (cell.get(field_name) or None) if field_name else None


class _Nodes:
    """Union-find over grid nodes; every column-0 node is the rail."""

    def __init__(self) -> None:
        self.parent: dict[tuple, tuple] = {}

    def find(self, node: tuple) -> tuple:
        if len(node) == 2 and node[1] == 0:
            node = _RAIL
        self.parent.setdefault(node, node)
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def join(self, first: tuple, second: tuple) -> None:
        a, b = self.find(first), self.find(second)
        if a != b:
            # Keep the rail as the representative so it stays recognizable.
            if b == _RAIL:
                a, b = b, a
            self.parent[b] = a


def build_network(cells: list[Cell], symbols: Mapping[str, str] | None = None,
                  spec: LadderSpec = LADDER_SPEC) -> tuple[LadderSeries, list[str]]:
    """Return the rung network and the element types left disconnected.

    `symbols` maps addresses to their declared symbol. An instruction's
    `operand` is the declared name when there is one (the model's contract:
    a tag/variable name), with the address kept as an `address=` annotation;
    an unnamed address stays as the operand.

    Raises NetworkUnresolved when the grid uses an unknown element type, has
    no output, or is not series-parallel.
    """
    symbols = symbols or {}

    def named(address: str | None) -> tuple[str | None, tuple[str, ...]]:
        return declared_name(address, symbols)
    cells = [cell for cell in cells if cell.get(spec.element_type) not in spec.ignored]
    unknown = sorted({cell.get(spec.element_type, "") for cell in cells
                      if not spec.known(cell.get(spec.element_type, ""))})
    if unknown:
        raise NetworkUnresolved("ladder_unknown_element", f"Unknown element type(s) {unknown}; no network built")

    def position(cell: Cell) -> tuple[int, int]:
        return int(cell[spec.row]), int(cell[spec.column])

    starts = {position(cell): cell for cell in cells}
    nodes = _Nodes()
    for cell in cells:
        kind = cell[spec.element_type]
        row, column = position(cell)
        right = column + spec.width(kind)
        connections = _connections(cell, spec)
        if "Down" in connections:
            nodes.join((row, right), (row + 1, right))
        if "Up" in connections:
            nodes.join((row, right), (row - 1, right))

    def instruction(cell: Cell, operation: LadderOperation, operand: str | None,
                    annotations: tuple[str, ...] = ()) -> LadderInstruction:
        row, column = position(cell)
        operand, address = named(operand)
        return LadderInstruction(operation=operation, source_mnemonic=cell[spec.element_type], operand=operand,
                                 annotations=annotations + address, position=LadderPosition(column=column, row=row))

    def element(cell: Cell, operation: LadderOperation, field_name: str | None) -> LadderInstruction:
        kind = cell[spec.element_type]
        if kind in spec.expression_fields:
            row, column = position(cell)
            return expression_instruction(cell.get(spec.expression_fields[kind], ""), kind, symbols,
                                          LadderPosition(column=column, row=row), spec)
        return instruction(cell, operation, _operand(cell, field_name))

    def wired_from(row: int, column: int) -> bool:
        # A cell starting there reads the node.
        cell = starts.get((row, column))
        return cell is not None and "Left" in _connections(cell, spec)

    edges: list[_Edge] = []
    for cell in cells:
        kind = cell[spec.element_type]
        row, column = position(cell)
        right = column + spec.width(kind)
        reads_left = "Left" in _connections(cell, spec)
        source = nodes.find((row, column))
        if kind in spec.wires and reads_left:
            target = nodes.find((row, right))
            # A wire whose ends are already joined does nothing.
            if target != source:
                edges.append(_Edge(source, target, LadderSeries(()), (row, column)))
        elif kind in spec.conditions and reads_left:
            operation, field_name = spec.conditions[kind]
            edges.append(_Edge(source, nodes.find((row, right)),
                               LadderSeries((element(cell, operation, field_name),)), (row, column)))
        elif kind in spec.outputs and reads_left:
            operation, field_name = spec.outputs[kind]
            # An output whose right side feeds another cell passes power on.
            target = nodes.find((row, right)) if wired_from(row, right) else _SINK
            edges.append(_Edge(source, target, LadderSeries((element(cell, operation, field_name),)),
                               (row, column)))
        elif kind in spec.blocks:
            pins = spec.blocks[kind]
            name, address = named(cell.get(spec.block_name) or None)
            for pin, offset in pins.outputs.items():
                if wired_from(row + offset, right):
                    reference = LadderInstruction(
                        operation=LadderOperation.BLOCK_OUTPUT_REFERENCE, source_mnemonic=kind,
                        operand=f"{name}.{pin}", annotations=address,
                        position=LadderPosition(column=column, row=row + offset))
                    edges.append(_Edge(_RAIL, nodes.find((row + offset, right)), LadderSeries((reference,)),
                                       (row + offset, column)))
    # Input pins last: a pin is wired when anything drives its node, which
    # may be another block's output, so every other edge must exist first.
    driven = {_RAIL} | {edge.target for edge in edges}
    for cell in cells:
        kind = cell[spec.element_type]
        if kind not in spec.blocks:
            continue
        row, column = position(cell)
        name, address = named(cell.get(spec.block_name) or None)
        for pin, offset in spec.blocks[kind].inputs.items():
            pin_node = nodes.find((row + offset, column))
            if pin_node in driven:
                edges.append(_Edge(pin_node, _SINK, LadderSeries((LadderInstruction(
                    operation=LadderOperation.FUNCTION_BLOCK_INPUT, source_mnemonic=kind, operand=f"{name}.{pin}",
                    annotations=address, position=LadderPosition(column=column, row=row)),)),
                    (row + offset, column)))
    edges, disconnected = _prune(edges)
    if not any(edge.target == _SINK for edge in edges):
        raise NetworkUnresolved("ladder_no_output", "No output is reachable from the rail; no network built")
    return _reduce(edges), disconnected


def _prune(edges: list[_Edge]) -> tuple[list[_Edge], list[str]]:
    """Drop edges on no rail-to-sink path; report the instructions they held."""
    forward, backward = {_RAIL}, {_SINK}
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge.source in forward and edge.target not in forward:
                forward.add(edge.target)
                changed = True
            if edge.target in backward and edge.source not in backward:
                backward.add(edge.source)
                changed = True
    kept = [edge for edge in edges if edge.source in forward and edge.target in backward]
    kept_ids = {id(edge) for edge in kept}
    disconnected = [element.source_mnemonic for edge in edges if id(edge) not in kept_ids
                    for element in edge.series.elements if isinstance(element, LadderInstruction)]
    return kept, disconnected


def _concat(first: LadderSeries, second: LadderSeries) -> LadderSeries:
    return LadderSeries(first.elements + second.elements)


def _first_position(series: LadderSeries) -> tuple[int, int] | None:
    """(row, column) of a branch's leftmost instruction, for drawn order."""
    for element in series.elements:
        if isinstance(element, LadderParallel):
            found = [position for branch in element.branches if (position := _first_position(branch))]
            if found:
                return min(found)
        elif element.position is not None:
            return element.position.row, element.position.column
    return None


def _parallel(branches: list[_Edge]) -> LadderSeries:
    # Nested parallels are flattened, then every branch is ordered by its own
    # leftmost instruction: reduction may merge branches in any sequence, so
    # an edge's order alone would leave earlier merges in the wrong place.
    keyed: list[tuple[tuple[int, int], LadderSeries]] = []
    for edge in branches:
        elements = edge.series.elements
        if len(elements) == 1 and isinstance(elements[0], LadderParallel):
            keyed.extend((_first_position(branch) or edge.order, branch) for branch in elements[0].branches)
        else:
            keyed.append((_first_position(edge.series) or edge.order, edge.series))
    keyed.sort(key=lambda item: item[0])
    return LadderSeries((LadderParallel(tuple(series for _, series in keyed)),))


def _reduce(edges: list[_Edge]) -> LadderSeries:
    while True:
        changed = False
        groups: dict[tuple, list[_Edge]] = {}
        for edge in edges:
            groups.setdefault((edge.source, edge.target), []).append(edge)
        if any(len(group) > 1 for group in groups.values()):
            edges = [group[0] if len(group) == 1 else
                     _Edge(group[0].source, group[0].target, _parallel(group), min(edge.order for edge in group))
                     for group in groups.values()]
            changed = True
        incoming: dict[tuple, list[_Edge]] = {}
        outgoing: dict[tuple, list[_Edge]] = {}
        for edge in edges:
            incoming.setdefault(edge.target, []).append(edge)
            outgoing.setdefault(edge.source, []).append(edge)
        for vertex in list(incoming):
            if vertex in (_RAIL, _SINK):
                continue
            if len(incoming[vertex]) == 1 and len(outgoing.get(vertex, [])) == 1:
                before, after = incoming[vertex][0], outgoing[vertex][0]
                edges = [edge for edge in edges if edge is not before and edge is not after]
                edges.append(_Edge(before.source, after.target, _concat(before.series, after.series), before.order))
                changed = True
                break
        if not changed:
            break
    if len(edges) == 1 and edges[0].source == _RAIL and edges[0].target == _SINK:
        return edges[0].series
    raise NetworkUnresolved("ladder_not_series_parallel",
                            "Grid wiring does not reduce to series and parallel branches; no network built")
