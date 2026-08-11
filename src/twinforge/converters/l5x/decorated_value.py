"""Shared promotion of scalar and composite L5X decorated values."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from twinforge.model import CompositeTagValue, CompositeTagValueNode, ScalarTagValue


InvalidValueHandler = Callable[[str, str, ET.Element], None]


def parse_composite_value(
    element: ET.Element,
    *,
    on_invalid: InvalidValueHandler | None = None,
) -> CompositeTagValue:
    """Promote an ordered decorated tree while retaining raw attributes."""

    return CompositeTagValue(root=_node(element, None, on_invalid))


def _node(
    element: ET.Element,
    inherited_data_type: str | None,
    on_invalid: InvalidValueHandler | None,
) -> CompositeTagValueNode:
    data_type = element.attrib.get("DataType") or inherited_data_type
    lexical_value = element.attrib.get("Value")
    value: ScalarTagValue | None = None
    if lexical_value is not None and data_type is not None:
        try:
            value = parse_scalar_value(data_type, lexical_value)
        except ValueError:
            if on_invalid is not None:
                on_invalid(data_type, lexical_value, element)
    return CompositeTagValueNode(
        source_kind=element.tag,
        name=element.attrib.get("Name"),
        index=element.attrib.get("Index"),
        data_type=data_type,
        dimensions=element.attrib.get("Dimensions"),
        radix=element.attrib.get("Radix"),
        lexical_value=lexical_value,
        value=value,
        children=tuple(_node(child, data_type, on_invalid) for child in element),
        raw_attributes=dict(element.attrib),
    )


def parse_scalar_value(
    data_type: str, lexical_value: str
) -> ScalarTagValue | None:
    """Parse one supported atomic Logix value without guessing unknown types."""

    normalized_type = data_type.upper()
    if normalized_type == "BOOL":
        normalized_value = lexical_value.strip().lower()
        if normalized_value in {"1", "true"}:
            return True
        if normalized_value in {"0", "false"}:
            return False
        raise ValueError(lexical_value)
    if normalized_type in {
        "SINT", "INT", "DINT", "LINT", "USINT", "UINT", "UDINT", "ULINT",
    }:
        value = lexical_value.strip()
        if "#" in value:
            base_text, digits = value.split("#", 1)
            return int(digits.replace("_", ""), int(base_text))
        return int(value.replace("_", ""), 0)
    if normalized_type in {"REAL", "LREAL"}:
        return float(lexical_value)
    if normalized_type in {"STRING", "WSTRING"}:
        return lexical_value
    return None
