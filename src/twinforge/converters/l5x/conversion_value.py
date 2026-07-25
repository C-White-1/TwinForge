"""Small, diagnostic-aware conversions shared by L5X converters.

The helpers in this module deliberately preserve the distinction between a
missing value and an invalid value. Missing optional data returns ``None``;
invalid source text additionally produces a conversion diagnostic.
"""

from __future__ import annotations

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.parsers.l5x.capture import CapturedSection


def emit_diagnostic(
    diagnostics: list[ConversionDiagnostic] | None,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    section: CapturedSection,
    field: str | None = None,
    raw_value: str | None = None,
) -> None:
    """Append a source-aware diagnostic when collection is enabled."""

    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=severity,
            code=code,
            message=message,
            object_name=section.attributes.get("Name"),
            field=field,
            raw_value=raw_value,
        )
    )


def optional_int(
    value: str | None,
    field: str,
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> int | None:
    """Convert an optional decimal integer without inventing a default."""

    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        emit_diagnostic(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_integer",
            f"{field} must be an integer, got {value!r}",
            section,
            field,
            value,
        )
        return None


def optional_bool(
    value: str | None,
    field: str,
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> bool | None:
    """Convert the L5X ``true``/``false`` lexical form when present."""

    if value == "true":
        return True
    if value == "false":
        return False
    if value is not None:
        emit_diagnostic(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_boolean",
            f"{field} must be 'true' or 'false', got {value!r}",
            section,
            field,
            value,
        )
    return None
