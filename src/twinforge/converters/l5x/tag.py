from __future__ import annotations

import xml.etree.ElementTree as ET

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Tag, TagValue
from twinforge.parsers.l5x.capture import CapturedSection

from .source_extension import captured_to_source_extension


_KNOWN_TAG_TYPES = {"Base", "Alias"}


def convert_tag(
    section: CapturedSection,
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> Tag:
    """Convert safe tag metadata while preserving every data representation."""

    if section.tag != "Tag":
        raise ValueError(f"expected a Tag section, got {section.tag!r}")

    name = section.attributes.get("Name", "")
    tag_type = section.attributes.get("TagType")
    if not name:
        _emit(
            diagnostics,
            DiagnosticSeverity.ERROR,
            "tag_missing_name",
            "tag is missing its Name attribute",
            None,
        )
    if tag_type is not None and tag_type not in _KNOWN_TAG_TYPES:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "unknown_tag_type",
            f"tag {name!r} uses unknown tag type {tag_type!r}",
            name,
            "TagType",
            tag_type,
        )
    if tag_type == "Alias" and "AliasFor" not in section.attributes:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "alias_target_missing",
            f"alias tag {name!r} does not specify AliasFor",
            name,
            "AliasFor",
        )
    if tag_type == "Base" and "DataType" not in section.attributes:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "base_tag_data_type_missing",
            f"base tag {name!r} does not specify DataType",
            name,
            "DataType",
        )

    return Tag(
        name=name,
        tag_type=tag_type,
        data_type=section.attributes.get("DataType"),
        dimensions=section.attributes.get("Dimensions"),
        radix=section.attributes.get("Radix"),
        constant=_optional_bool(section, "Constant", diagnostics),
        alias_for=section.attributes.get("AliasFor"),
        external_access=section.attributes.get("ExternalAccess"),
        permission_set=section.attributes.get("PermissionSet"),
        description=_description(section),
        initial_value=_initial_value(section, diagnostics),
        source_extensions=[captured_to_source_extension(section)],
    )


def _description(section: CapturedSection) -> str | None:
    descriptions = section.elements.get("Description", [])
    if not descriptions or descriptions[0].text is None:
        return None
    return descriptions[0].text.strip()


def _initial_value(
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> TagValue | None:
    for data in section.elements.get("Data", []):
        if data.attributes.get("Format") != "Decorated":
            continue
        for child in data.ordered_children:
            if not isinstance(child, ET.Element) or child.tag != "DataValue":
                continue
            lexical_value = child.attrib.get("Value")
            data_type = child.attrib.get("DataType") or section.attributes.get(
                "DataType"
            )
            if lexical_value is None or data_type is None:
                return None
            try:
                value = _parse_scalar_value(data_type, lexical_value)
            except ValueError:
                _emit(
                    diagnostics,
                    DiagnosticSeverity.WARNING,
                    "invalid_scalar_tag_value",
                    (
                        f"tag {section.attributes.get('Name', '')!r} has an "
                        f"invalid {data_type} decorated value"
                    ),
                    section.attributes.get("Name"),
                    "Data",
                    lexical_value,
                )
                return None
            if value is None:
                return None
            return TagValue(
                value=value,
                data_type=data_type.upper(),
                lexical_value=lexical_value,
                radix=child.attrib.get("Radix")
                or section.attributes.get("Radix"),
            )
    return None


def _parse_scalar_value(
    data_type: str, lexical_value: str
) -> bool | int | float | str | None:
    normalized_type = data_type.upper()
    if normalized_type == "BOOL":
        normalized_value = lexical_value.strip().lower()
        if normalized_value in {"1", "true"}:
            return True
        if normalized_value in {"0", "false"}:
            return False
        raise ValueError(lexical_value)
    if normalized_type in {
        "SINT",
        "INT",
        "DINT",
        "LINT",
        "USINT",
        "UINT",
        "UDINT",
        "ULINT",
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


def _optional_bool(
    section: CapturedSection,
    field: str,
    diagnostics: list[ConversionDiagnostic] | None,
) -> bool | None:
    value = section.attributes.get(field)
    if value == "true":
        return True
    if value == "false":
        return False
    if value is not None:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_boolean",
            f"{field} must be 'true' or 'false', got {value!r}",
            section.attributes.get("Name"),
            field,
            value,
        )
    return None


def _emit(
    diagnostics: list[ConversionDiagnostic] | None,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    object_name: str | None,
    field: str | None = None,
    raw_value: str | None = None,
) -> None:
    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=severity,
            code=code,
            message=message,
            object_name=object_name,
            field=field,
            raw_value=raw_value,
        )
    )
