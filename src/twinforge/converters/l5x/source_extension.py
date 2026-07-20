from __future__ import annotations

import xml.etree.ElementTree as ET

from twinforge.model import SourceExtension, SourceNode
from twinforge.parsers.l5x.capture import CapturedSection


def captured_to_source_extension(
    section: CapturedSection,
    *,
    format: str = "l5x",
) -> SourceExtension:
    """Create a lossless model-side snapshot of a captured source section."""

    return SourceExtension(format=format, root=_captured_node(section))


def element_to_source_extension(
    element: ET.Element,
    *,
    format: str = "l5x",
) -> SourceExtension:
    """Snapshot an XML element when no captured schema section exists."""

    return SourceExtension(format=format, root=_source_node(element))


def _captured_node(section: CapturedSection) -> SourceNode:
    attributes = (
        dict(section.raw_attributes)
        if section.raw_attributes is not None
        else {**section.attributes, **section.extra_attributes}
    )
    return SourceNode(
        name=section.tag,
        attributes=attributes,
        text=section.text,
        tail=section.tail,
        children=[_source_node(child) for child in section.ordered_children],
    )


def _source_node(element: CapturedSection | ET.Element) -> SourceNode:
    if isinstance(element, CapturedSection):
        return _captured_node(element)
    return SourceNode(
        name=element.tag,
        attributes=dict(element.attrib),
        text=element.text,
        tail=element.tail,
        children=[_source_node(child) for child in element],
    )
