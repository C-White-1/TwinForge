"""Schema validation for target-independent PLCopen XML documents."""

from __future__ import annotations

from pathlib import Path


class PLCopenValidationError(ValueError):
    """Raised when a PLCopen document does not satisfy its selected XSD."""


class PLCopenValidationUnavailable(RuntimeError):
    """Raised when the optional XML validation dependency is unavailable."""


def validate_plcopen_xml(xml: str | bytes, schema_path: str | Path) -> None:
    """Validate serialized PLCopen XML against an explicitly supplied XSD."""

    try:
        import lxml.etree as etree
    except ImportError as error:
        raise PLCopenValidationUnavailable(
            "XSD validation requires the optional 'lxml' package"
        ) from error
    schema = etree.XMLSchema(etree.parse(str(schema_path)))
    document = etree.fromstring(
        xml.encode("utf-8") if isinstance(xml, str) else xml
    )
    if not schema.validate(document):
        messages = "; ".join(entry.message for entry in schema.error_log)
        raise PLCopenValidationError(messages)
