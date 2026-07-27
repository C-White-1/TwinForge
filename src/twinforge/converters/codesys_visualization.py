"""Convert parsed CODESYS-native visualizations to the neutral model."""

import xml.etree.ElementTree as ET

from twinforge.model import (
    SourceExtension,
    SourceNode,
    VisualizationBinding,
    VisualizationBindingRole,
    VisualizationCanvas,
    VisualizationControl,
    VisualizationControlKind,
    VisualizationDocument,
    VisualizationGeometry,
    VisualizationInteraction,
    VisualizationInteractionKind,
)
from twinforge.parsers.codesys_native import (
    CodesysNativeExport,
    CodesysVisualizationAction,
    CodesysVisualizationElement,
)


def convert_codesys_visualization(
    source: CodesysNativeExport,
) -> VisualizationDocument:
    """Lower decoded evidence without carrying CODESYS types into the model."""
    manager = source.managers[0] if source.managers else None
    document = VisualizationDocument(
        theme=manager.style if manager is not None else None,
        source_extensions=[
            _extension(
                source.source_xml,
                {
                    "profile": source.profile,
                    "profile_mappings_applied": (
                        source.profile_mappings_applied
                    ),
                },
            )
        ],
    )
    for visualization in source.visualizations:
        canvas = VisualizationCanvas(
            name=visualization.name,
            width=visualization.width,
            height=visualization.height,
            source_extensions=[_extension(visualization.raw_xml)],
        )
        canvas.controls.extend(
            _convert_control(element, source)
            for element in visualization.elements
        )
        document.canvases.append(canvas)
    return document


def _convert_control(
    element: CodesysVisualizationElement,
    source: CodesysNativeExport,
) -> VisualizationControl:
    properties = element.properties
    interactions = [
        _convert_interaction(action, element.bindings)
        for action in element.actions
    ]
    action_operands = {
        interaction.operand
        for interaction in interactions
        if interaction.operand is not None
    }
    default_role = (
        VisualizationBindingRole.VALUE
        if not interactions
        else VisualizationBindingRole.COMMAND
    )
    bindings = [
        VisualizationBinding(
            expression=expression,
            role=(
                _binding_role(expression, interactions)
                if expression in action_operands
                else default_role
            ),
        )
        for expression in element.bindings
    ]
    identifier = element.identifier or (
        f"element_{element.element_id}"
        if element.element_id is not None
        else "anonymous_element"
    )
    return VisualizationControl(
        identifier=identifier,
        kind=_control_kind(element.element_type),
        source_type=element.element_type,
        geometry=VisualizationGeometry(
            x=_integer(properties.get("x")),
            y=_integer(properties.get("y")),
            width=_integer(properties.get("width")),
            height=_integer(properties.get("height")),
        ),
        text=properties.get("text") or None,
        bindings=bindings,
        interactions=interactions,
        source_extensions=[
            _extension(
                element.raw_xml,
                {
                    "profile": source.profile,
                    "profile_mappings_applied": (
                        source.profile_mappings_applied
                    ),
                    "numeric_properties": dict(
                        element.numeric_properties
                    ),
                },
            )
        ],
    )


def _convert_interaction(
    action: CodesysVisualizationAction,
    bindings: tuple[str, ...],
) -> VisualizationInteraction:
    properties = action.properties
    if action.kind == "Toggle":
        kind = VisualizationInteractionKind.TOGGLE
        operand = bindings[0] if bindings else None
    elif action.kind == "InputBox":
        kind = VisualizationInteractionKind.VALUE_INPUT
        operand = properties.get("InputBoxVariable")
    else:
        kind = VisualizationInteractionKind.UNKNOWN
        operand = bindings[0] if bindings else None
    return VisualizationInteraction(
        kind=kind,
        operand=operand,
        value_format=properties.get("Format"),
        minimum=properties.get("InputBoxMin"),
        maximum=properties.get("InputBoxMax"),
        prompt=properties.get("InputBoxDialogTitle"),
        source_extensions=(
            _extension(
                action.raw_xml,
                {"source_kind": action.kind},
            ),
        ),
    )


def _binding_role(
    expression: str,
    interactions: list[VisualizationInteraction],
) -> VisualizationBindingRole:
    if any(
        interaction.operand == expression
        and interaction.kind is VisualizationInteractionKind.VALUE_INPUT
        for interaction in interactions
    ):
        return VisualizationBindingRole.INPUT
    return VisualizationBindingRole.COMMAND


def _control_kind(source_type: str | None) -> VisualizationControlKind:
    return {
        "Button": VisualizationControlKind.BUTTON,
        "Textfield": VisualizationControlKind.TEXT_INPUT,
        "Lamp1": VisualizationControlKind.INDICATOR,
        "Label": VisualizationControlKind.LABEL,
    }.get(source_type or "", VisualizationControlKind.UNKNOWN)


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _extension(
    xml: str,
    metadata: dict[str, object] | None = None,
) -> SourceExtension:
    root = ET.fromstring(xml)
    return SourceExtension(
        format="codesys-native",
        root=_source_node(root),
        metadata=metadata or {},
    )


def _source_node(element: ET.Element) -> SourceNode:
    return SourceNode(
        name=element.tag,
        attributes=dict(element.attrib),
        text=element.text,
        tail=element.tail,
        children=[_source_node(child) for child in element],
    )
