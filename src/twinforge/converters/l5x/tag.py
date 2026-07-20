from __future__ import annotations

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Tag
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
        source_extensions=[captured_to_source_extension(section)],
    )


def _description(section: CapturedSection) -> str | None:
    descriptions = section.elements.get("Description", [])
    if not descriptions or descriptions[0].text is None:
        return None
    return descriptions[0].text.strip()


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
