"""Promote observed graphical objects while retaining unresolved connections."""
from twinforge.model import GraphicalDiagram, GraphicalLink, GraphicalLinkEndpoint, GraphicalObject, GraphicalPin, LadderPosition
from twinforge.schema.control_expert.graphical import GRAPHICAL_SPEC, GraphicalSpec

from .capture import CapturedSection, Diagnostic
from .evidence import source_extension as _extension


def parse_diagrams(
    source: CapturedSection, *, spec: GraphicalSpec = GRAPHICAL_SPEC,
) -> tuple[list[GraphicalDiagram], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str, node: CapturedSection) -> None:
        diagnostics.append(Diagnostic(code, message, node.source))

    def number(node: CapturedSection, name: str) -> int | None:
        value = node.raw_attributes.get(name)
        if value is None:
            return None
        if not value.isascii() or not value.isdecimal():
            report("invalid_graphical_number", f"{name}={value!r} is not a nonnegative integer", node)
            return None
        return int(value)

    def object_from(node: CapturedSection, kind: str) -> GraphicalObject:
        attrs = node.raw_attributes
        obj = GraphicalObject(
            kind=kind, instance_name=attrs.get("instanceName"),
            type_name=(attrs.get("typeName") if kind == "block" else
                       attrs.get("typeCoil") if kind == "coil" else attrs.get("typeContact")),
            operand=attrs.get("coilVariableName") if kind == "coil" else attrs.get("contactVariableName"),
            text=node.text if kind == "annotation" else None,
            width=number(node, "width"), height=number(node, "height"),
            source_extensions=[_extension(node)],
        )
        for child in node.ordered_children:
            if child.tag not in {spec.position, spec.description} and not child.tag.startswith("#"):
                report("unclassified_graphical_detail", "Unknown object detail retained", child)
        positions = [c for c in node.ordered_children if c.tag == spec.position]
        if len(positions) == 1:
            x, y = number(positions[0], "posX"), number(positions[0], "posY")
            if x is not None and y is not None:
                obj.position = LadderPosition(x, y)
        elif len(positions) > 1:
            report("ambiguous_graphical_position", "Multiple positions retained without choosing one", node)
        descriptions = [c for c in node.ordered_children if c.tag == spec.description]
        if len(descriptions) > 1:
            report("ambiguous_block_interface", "Multiple block descriptions retained without merging pins", node)
            return obj
        directions = dict(spec.pins)
        if descriptions:
            obj.execution_after = descriptions[0].raw_attributes.get(spec.execution_after_attribute)
            for pin in descriptions[0].ordered_children:
                if pin.tag not in directions:
                    report("unclassified_graphical_pin", "Unknown block interface content retained", pin)
                    continue
                value = pin.raw_attributes.get("invertedPin")
                inverted = {"true": True, "false": False}.get(value or "")
                if value is not None and inverted is None:
                    report("unknown_pin_inversion", f"Unsupported inversion value {value!r}", pin)
                obj.pins.append(GraphicalPin(
                    name=pin.raw_attributes.get("formalParameter"),
                    direction=directions[pin.tag], expression=pin.raw_attributes.get("effectiveParameter"),
                    inverted=inverted, source_extensions=[_extension(pin)],
                    role=next((role for direction, name, role in spec.execution_roles
                               if direction == directions[pin.tag]
                               and name == pin.raw_attributes.get("formalParameter")), "data"),
                ))
        return obj

    kinds = dict(spec.objects)

    def objects(node: CapturedSection, diagram: GraphicalDiagram, links: list[CapturedSection]) -> None:
        for child in node.ordered_children:
            if child.tag in kinds:
                diagram.objects.append(object_from(child, kinds[child.tag]))
            elif child.tag in spec.containers:
                objects(child, diagram, links)
            elif child.tag == spec.link:
                links.append(child)
            elif child.tag not in spec.layout_nodes and not child.tag.startswith("#"):
                report("unclassified_graphical_object", "Unknown graphical content retained without interpretation", child)

    def resolve_endpoint(link: CapturedSection, diagram: GraphicalDiagram, role: str, tag: str) -> GraphicalLinkEndpoint:
        expected_direction = "output" if role == "source" else "input"
        matches = [c for c in link.ordered_children if c.tag == tag]
        if len(matches) != 1:
            report("invalid_graphical_link_endpoint_count",
                   f"Explicit link requires one {role}; found {len(matches)}", link)
            return GraphicalLinkEndpoint()
        node = matches[0]
        object_name = node.raw_attributes.get(spec.link_object_attribute)
        pin_name = node.raw_attributes.get(spec.link_pin_attribute)
        object_matches = [i for i, obj in enumerate(diagram.objects) if obj.instance_name == object_name]
        status: str
        object_index = pin_index = None
        if not object_name or not object_matches:
            status = "missing_object"
        elif len(object_matches) > 1:
            status = "ambiguous_object"
        else:
            object_index = object_matches[0]
            pin_matches = [i for i, pin in enumerate(diagram.objects[object_index].pins)
                           if pin.name == pin_name and pin.direction == expected_direction]
            if not pin_name or not pin_matches:
                status = "missing_pin"
            elif len(pin_matches) > 1:
                status = "ambiguous_pin"
            else:
                status, pin_index = "resolved", pin_matches[0]
        if status != "resolved":
            report("unresolved_graphical_link_endpoint", f"{role}: {status}", link)
        return GraphicalLinkEndpoint(object_name, pin_name, status, object_index, pin_index)

    diagrams: list[GraphicalDiagram] = []
    languages = dict(spec.networks)
    for network in source.ordered_children:
        if network.tag not in languages:
            if not network.tag.startswith("#"):
                report("unclassified_graphical_network", "Unknown graphical network retained", network)
            continue
        diagram = GraphicalDiagram(language=languages[network.tag], source_extensions=[_extension(network)])
        diagnostic_start = len(diagnostics)
        pending_links: list[CapturedSection] = []
        objects(network, diagram, pending_links)
        for link in pending_links:
            diagram.links.append(GraphicalLink(
                source=resolve_endpoint(link, diagram, "source", spec.link_source),
                destination=resolve_endpoint(link, diagram, "destination", spec.link_destination),
                source_extensions=[_extension(link)],
            ))
        diagrams.append(diagram)
        blocks = [i for i, obj in enumerate(diagram.objects) if obj.kind == "block"]
        # A single FBD block has no relative intra-network block ordering to
        # resolve. Do not generalize this to section order, enable conditions,
        # missing wiring, or a network with unrecognized/control-flow objects.
        if (diagram.language == "FBD" and len(blocks) == 1
                and len(diagnostics) == diagnostic_start
                and all(c.tag in kinds for c in network.ordered_children)
                and all(obj.kind in {"block", "annotation"} for obj in diagram.objects)
                and not diagram.objects[blocks[0]].execution_after):
            diagram.execution_order = blocks
            diagram.execution_order_resolved = True
            diagram.execution_order_basis = "single_block_network"
        report("unresolved_graphical_connections",
               "Pin directions and expressions extracted; graphical wiring remains unresolved", network)
        # Block order may still resolve from whole-project shared-variable
        # dataflow once known; the caller reports "unresolved_block_order"
        # centrally after that analysis runs, not eagerly here.
    if not diagrams:
        report("missing_graphical_network", "No supported graphical network found", source)
    return diagrams, diagnostics
