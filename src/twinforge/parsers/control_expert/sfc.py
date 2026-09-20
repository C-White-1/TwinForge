"""Map observed SFC structure without resolving layout, links or runtime behavior."""
from twinforge.model.sequential import SequentialChart, SequentialElement
from twinforge.schema.control_expert.sfc import SFC_SPEC, SequentialSpec

from .capture import CapturedSection, Diagnostic
from .evidence import source_extension


def parse_charts(
    section: CapturedSection, spec: SequentialSpec = SFC_SPEC,
) -> tuple[list[SequentialChart], list[Diagnostic]]:
    rules = {tag: (kind, attributes) for tag, kind, attributes in spec.elements}

    diagnostics: list[Diagnostic] = []
    origins: dict[int, CapturedSection] = {}
    definitions = [child for child in section.ordered_children if child.tag == spec.definitions]
    names: dict[str, list[int]] = {}
    for index, definition in enumerate(definitions):
        name = definition.raw_attributes.get("name", "")
        if name:
            names.setdefault(name.casefold(), []).append(index)
        else:
            diagnostics.append(Diagnostic("missing_sfc_definition_name",
                                          "Transition definition has no name; retained", definition.source))
    for indices in names.values():
        if len(indices) > 1:
            for index in indices:
                diagnostics.append(Diagnostic("duplicate_sfc_definition",
                                              "Transition definition name is ambiguous; retained",
                                              definitions[index].source))

    def convert(node: CapturedSection, parent_kind: str | None = None) -> SequentialElement:
        kind, attributes = rules.get(node.tag, ("unknown", ()))
        result = SequentialElement(
            kind=kind,
            properties={target: node.raw_attributes[source] for source, target in attributes
                        if source in node.raw_attributes},
            text=node.text,
            children=[convert(child, kind) for child in node.ordered_children],
            source_extensions=[source_extension(node)],
        )
        origins[id(result)] = node
        if kind == "transition_reference" and parent_kind == "condition":
            matches = names.get((node.text or "").casefold(), [])
            result.reference_status = "resolved" if len(matches) == 1 else "ambiguous" if matches else "missing"
            if len(matches) == 1:
                result.target_definition_index = matches[0]
            else:
                diagnostics.append(Diagnostic(
                    "unresolved_sfc_transition_reference",
                    f"{node.text!r}: {result.reference_status} chart-local transition definition",
                    node.source,
                ))
        return result

    charts = [SequentialChart(
        name=chart.raw_attributes.get("name"),
        elements=[convert(child) for child in chart.ordered_children],
        transition_definitions=[convert(child) for child in section.ordered_children
                                if child.tag == spec.definitions],
        source_extensions=[source_extension(section)],
    ) for chart in section.ordered_children if chart.tag == spec.charts]

    endpoint_types = dict(spec.endpoint_types)

    def position(element: SequentialElement) -> tuple[str, str] | None:
        positions = [child for child in element.children if child.kind == "position"]
        if len(positions) != 1:
            return None
        properties = positions[0].properties
        x, y = properties.get("x"), properties.get("y")
        return (x, y) if x and y else None

    for chart in charts:
        for network_index, network in enumerate(chart.elements):
            if network.kind != "network":
                continue
            for link in network.children:
                if link.kind != "explicit_link":
                    continue
                for role in ("link_source", "link_destination"):
                    endpoints = [child for child in link.children if child.kind == role]
                    if len(endpoints) != 1:
                        for endpoint in endpoints:
                            endpoint.reference_status = "ambiguous"
                        diagnostics.append(Diagnostic(
                            "invalid_sfc_link_endpoint_count",
                            f"Explicit link requires one {role}; found {len(endpoints)}",
                            origins[id(link)].source,
                        ))
                        continue
                    endpoint = endpoints[0]
                    target_kind = endpoint_types.get(endpoint.properties.get("source_object_type", ""))
                    coordinates = position(endpoint)
                    matches = [index for index, obj in enumerate(network.children)
                               if target_kind is not None and coordinates is not None
                               and obj.kind == target_kind and position(obj) == coordinates]
                    status = ("unsupported_type" if target_kind is None else
                              "invalid_position" if coordinates is None else
                              "resolved" if len(matches) == 1 else
                              "ambiguous" if matches else "missing")
                    endpoint.reference_status = status
                    if status == "resolved":
                        endpoint.target_element_path = [network_index, matches[0]]
                    else:
                        diagnostics.append(Diagnostic(
                            "unresolved_sfc_link_endpoint", f"{role}: {status}", origins[id(endpoint)].source,
                        ))
    return charts, diagnostics
