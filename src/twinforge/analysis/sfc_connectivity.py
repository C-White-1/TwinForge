"""Resolve SFC step/transition connectivity from evidenced grid adjacency and
explicit links only.

A step or transition's successor is resolved when exactly one candidate exists:
the unique flow object at the next grid row in the same column, or a resolved
explicit link sourced from it. Divergence uses an `alternative_branch` element
colocated with the first column's transition; convergence uses a linked
`alternative_join`, resolved onward to the object following its own anchor
position. Both require `relative_position == "0"`, the only value evidenced in
the corpus (see the capture specification); any other shape, any row missing
an expected column, or any conflicting pair of candidates stays diagnosed and
unresolved rather than guessed. This proves grid/link adjacency only -- not
memory effects, timing or runtime truth.
"""
from dataclasses import dataclass

from twinforge.model import Controller
from twinforge.model.sequential import SequentialChart, SequentialEdge, SequentialElement

_FLOW_KINDS = frozenset({"step", "transition"})


@dataclass(frozen=True)
class SFCConnectivityIssue:
    program_name: str
    routine_name: str
    chart_index: int
    element_path: list[int]
    code: str
    detail: str


def _position(element: SequentialElement) -> tuple[int, int] | None:
    positions = [child for child in element.children if child.kind == "position"]
    if len(positions) != 1:
        return None
    x, y = positions[0].properties.get("x"), positions[0].properties.get("y")
    if x is None or y is None:
        return None
    try:
        return int(x), int(y)
    except ValueError:
        return None


def _explicit_link_edges(network: SequentialElement, network_index: int) -> dict[tuple[int, int], list[int]]:
    edges: dict[tuple[int, int], list[int]] = {}
    for link in network.children:
        if link.kind != "explicit_link":
            continue
        sources = [child for child in link.children if child.kind == "link_source"]
        destinations = [child for child in link.children if child.kind == "link_destination"]
        if len(sources) != 1 or len(destinations) != 1:
            continue
        source, destination = sources[0], destinations[0]
        source_path, destination_path = source.target_element_path, destination.target_element_path
        if (source.reference_status == "resolved" and destination.reference_status == "resolved"
                and source_path is not None and destination_path is not None
                and len(source_path) == 2 and source_path[0] == network_index):
            edges[(source_path[0], source_path[1])] = destination_path
    return edges


def _resolve_network(
    network: SequentialElement, network_index: int,
) -> tuple[list[SequentialEdge], list[tuple[list[int], str, str]]]:
    edges: list[SequentialEdge] = []
    issues: list[tuple[list[int], str, str]] = []

    kinds: dict[int, str] = {}
    positions: dict[int, tuple[int, int]] = {}
    by_position: dict[tuple[int, int], list[int]] = {}
    for index, obj in enumerate(network.children):
        if obj.kind not in _FLOW_KINDS | {"alternative_branch", "alternative_join"}:
            continue
        kinds[index] = obj.kind
        pos = _position(obj)
        if pos is not None:
            positions[index] = pos
            by_position.setdefault(pos, []).append(index)

    link_edges = _explicit_link_edges(network, network_index)

    def flow_at(pos: tuple[int, int]) -> int | None:
        candidates = [i for i in by_position.get(pos, []) if kinds[i] in _FLOW_KINDS]
        return candidates[0] if len(candidates) == 1 else None

    def branch_at(pos: tuple[int, int]) -> int | None:
        candidates = [i for i in by_position.get(pos, []) if kinds[i] == "alternative_branch"]
        return candidates[0] if len(candidates) == 1 else None

    def branch_targets(branch_index: int, pos: tuple[int, int]) -> list[int] | None:
        obj = network.children[branch_index]
        if obj.properties.get("relative_position") != "0":
            return None
        try:
            width = int(obj.properties.get("width", ""))
        except ValueError:
            return None
        if width <= 0:
            return None
        targets = []
        for x in range(pos[0], pos[0] + width):
            candidates = [i for i in by_position.get((x, pos[1]), []) if kinds[i] == "transition"]
            if len(candidates) != 1:
                return None
            targets.append(candidates[0])
        return targets

    def join_successor(join_index: int) -> int | None:
        obj = network.children[join_index]
        pos = positions.get(join_index)
        if pos is None or obj.properties.get("relative_position") != "0":
            return None
        return flow_at((pos[0], pos[1] + 1))

    for index, kind in kinds.items():
        if kind not in _FLOW_KINDS:
            continue
        source_path = [network_index, index]
        pos = positions.get(index)
        if pos is None:
            issues.append((source_path, "unresolved_sfc_successor", "no grid position recorded"))
            continue

        linked = link_edges.get((network_index, index))
        next_pos = (pos[0], pos[1] + 1)

        if kind == "step":
            branch_index = branch_at(next_pos)
            if branch_index is not None:
                if linked is not None:
                    issues.append((source_path, "ambiguous_sfc_successor",
                                   "step: alternative_branch conflicts with an explicit link"))
                    continue
                targets = branch_targets(branch_index, next_pos)
                if targets is None:
                    issues.append((source_path, "unsupported_sfc_branch_position",
                                   "alternative_branch width/relative_position not evidenced or row incomplete"))
                    continue
                edges.extend(SequentialEdge(source_path, [network_index, t], "grid_adjacency") for t in targets)
                continue
            plain_index = flow_at(next_pos)
            plain_ok = plain_index is not None and kinds[plain_index] == "transition"
            if plain_ok and linked is not None:
                issues.append((source_path, "ambiguous_sfc_successor",
                               "step: plain adjacency and explicit link disagree"))
            elif plain_ok and plain_index is not None:
                edges.append(SequentialEdge(source_path, [network_index, plain_index], "grid_adjacency"))
            elif linked is not None:
                if linked[0] == network_index and kinds.get(linked[1]) == "transition":
                    edges.append(SequentialEdge(source_path, linked, "explicit_link"))
                else:
                    issues.append((source_path, "unresolved_sfc_successor",
                                   "explicit link destination is not a transition in this network"))
            else:
                issues.append((source_path, "unresolved_sfc_successor", "no adjacent or linked transition"))
            continue

        # transition
        plain_index = flow_at(next_pos)
        plain_ok = plain_index is not None and kinds[plain_index] == "step"
        if plain_ok and linked is not None:
            issues.append((source_path, "ambiguous_sfc_successor",
                           "transition: plain adjacency and explicit link disagree"))
        elif plain_ok and plain_index is not None:
            edges.append(SequentialEdge(source_path, [network_index, plain_index], "grid_adjacency"))
        elif linked is not None:
            if linked[0] != network_index:
                issues.append((source_path, "unresolved_sfc_successor", "explicit link crosses network"))
                continue
            destination_kind = kinds.get(linked[1])
            if destination_kind == "step":
                edges.append(SequentialEdge(source_path, linked, "explicit_link"))
            elif destination_kind == "alternative_join":
                resolved = join_successor(linked[1])
                if resolved is None:
                    issues.append((source_path, "unsupported_sfc_branch_position",
                                   "alternative_join width/relative_position not evidenced or has no successor"))
                else:
                    edges.append(SequentialEdge(source_path, [network_index, resolved], "join_indirection"))
            else:
                issues.append((source_path, "unresolved_sfc_successor",
                               f"explicit link destination kind {destination_kind!r} is not a step or alternative_join"))
        else:
            issues.append((source_path, "unresolved_sfc_successor", "no adjacent step or explicit link"))

    return edges, issues


def resolve_sfc_connectivity(controller: Controller) -> list[SFCConnectivityIssue]:
    issues: list[SFCConnectivityIssue] = []
    for program in controller.programs.values():
        for routine in program.routines.values():
            for chart_index, chart in enumerate(routine.sequential_charts):
                issues.extend(_resolve_chart(program.name, routine.name, chart_index, chart))
    return issues


def _resolve_chart(
    program_name: str, routine_name: str, chart_index: int, chart: SequentialChart,
) -> list[SFCConnectivityIssue]:
    chart.connectivity_edges = []
    chart.connectivity_resolved = False
    edges: list[SequentialEdge] = []
    node_issues: list[tuple[list[int], str, str]] = []
    for network_index, network in enumerate(chart.elements):
        if network.kind != "network":
            continue
        network_edges, network_issues = _resolve_network(network, network_index)
        edges.extend(network_edges)
        node_issues.extend(network_issues)
    chart.connectivity_edges = edges
    chart.connectivity_resolved = not node_issues
    return [SFCConnectivityIssue(program_name, routine_name, chart_index, path, code, detail)
            for path, code, detail in node_issues]
