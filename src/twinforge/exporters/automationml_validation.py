"""CAEX XSD validation for generated AutomationML documents."""

from __future__ import annotations

from pathlib import Path


class AutomationMLValidationError(ValueError):
    """Raised when structural or semantic AutomationML validation fails."""


class AutomationMLValidationUnavailable(RuntimeError):
    """Raised when the optional CAEX XSD validator is unavailable."""


def validate_automationml_xml(
    xml: str | bytes,
    schema_path: str | Path,
) -> None:
    """Validate XML structure and ordering against an explicit CAEX XSD."""

    try:
        import lxml.etree as etree
    except ImportError as error:
        raise AutomationMLValidationUnavailable(
            "CAEX XSD validation requires the optional 'lxml' package"
        ) from error
    try:
        schema = etree.XMLSchema(etree.parse(str(schema_path)))
        document = etree.fromstring(
            xml.encode("utf-8") if isinstance(xml, str) else xml
        )
    except (etree.XMLSchemaParseError, etree.XMLSyntaxError) as error:
        raise AutomationMLValidationError(str(error)) from error
    if not schema.validate(document):
        messages = "; ".join(
            f"line {entry.line}: {entry.message}"
            for entry in schema.error_log
        )
        raise AutomationMLValidationError(messages)
