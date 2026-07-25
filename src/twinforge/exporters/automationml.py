"""Public AutomationML export façade.

Document construction, class libraries, signal/I/O generation, deterministic
identity, structural validation, and semantic validation are implemented in
focused modules. This façade preserves TwinForge's original public API.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from twinforge.model import Controller

from .automationml_hierarchy import build_automationml_document
from .automationml_reference_validation import (
    validate_automationml_references,
)
from .automationml_types import (
    AUTOMATIONML_VERSION,
    CAEX_NAMESPACE,
    CAEX_SCHEMA_VERSION,
    AutomationMLExportResult,
)
from .automationml_validation import (
    AutomationMLValidationError,
    AutomationMLValidationUnavailable,
    validate_automationml_xml,
)

__all__ = [
    "AUTOMATIONML_VERSION",
    "CAEX_NAMESPACE",
    "CAEX_SCHEMA_VERSION",
    "AutomationMLExporter",
    "AutomationMLExportResult",
    "AutomationMLValidationError",
    "AutomationMLValidationUnavailable",
    "validate_automationml_references",
    "validate_automationml_xml",
]


class AutomationMLExporter:
    """Export the vendor-neutral model as AutomationML 2.1 / CAEX 3.0."""

    def export(
        self,
        controller: Controller,
        *,
        project_name: str | None = None,
        plcopen_path: str | Path | None = None,
        base_library_path: str | Path | None = None,
        destination: str | Path | None = None,
        last_writing_time: datetime | None = None,
    ) -> AutomationMLExportResult:
        """Build, serialize, and optionally write one AutomationML document."""

        if base_library_path is None:
            raise ValueError(
                "AutomationML 2.1 base_library_path is required"
            )
        name = project_name or controller.name or "TwinForgeProject"
        writing_time = last_writing_time or datetime.now(timezone.utc)
        destination_path = (
            Path(destination) if destination is not None else None
        )
        root = build_automationml_document(
            controller,
            project_name=name,
            file_name=(
                destination_path.name
                if destination_path is not None
                else f"{name}.aml"
            ),
            plcopen_path=plcopen_path,
            base_library_path=base_library_path,
            last_writing_time=writing_time,
        )
        ET.indent(root, space="  ")
        ET.register_namespace("", CAEX_NAMESPACE)
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
        if destination_path is not None:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_text(xml, encoding="utf-8")
        return AutomationMLExportResult(
            xml=xml,
            destination=destination_path,
        )
