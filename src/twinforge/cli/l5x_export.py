"""Installed adapters for exporting L5X models to target formats."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import os
from pathlib import Path
from typing import TextIO

from twinforge.exporters import (
    AutomationMLExporter,
    AutomationMLValidationError,
    AutomationMLValidationUnavailable,
    PLCopenExporter,
    PLCopenProfile,
    PLCopenValidationError,
    PLCopenValidationUnavailable,
    validate_plcopen_xml,
    validate_automationml_references,
    validate_automationml_xml,
)
from twinforge.model import Controller
from twinforge.parsers.l5x import L5XParser
from twinforge.targets.openplc import (
    OpenPLCNativeProjectExporter,
    OpenPLCNativeUnsupportedError,
)


class L5XExportError(RuntimeError):
    """Raised when an installed L5X export operation cannot complete."""


_PROFILES = {
    "plcopen": PLCopenProfile.STANDARD_201,
    "codesys": PLCopenProfile.CODESYS,
}


def export_l5x_target(
    source: Path,
    *,
    target: str,
    destination: Path,
    schema_path: Path | None,
    compile_only: bool,
    base_library_path: Path | None,
    plcopen_reference: Path | None,
    stdout: TextIO,
) -> None:
    """Export a Controller L5X using one explicit target adapter."""
    try:
        if target == "openplc":
            _export_openplc_native(
                source,
                destination=destination,
                schema_path=schema_path,
                compile_only=compile_only,
                stdout=stdout,
            )
            return
        if target == "automationml":
            _export_automationml(
                source,
                destination=destination,
                schema_path=schema_path,
                compile_only=compile_only,
                base_library_path=base_library_path,
                plcopen_reference=plcopen_reference,
                stdout=stdout,
            )
            return

        if base_library_path is not None or plcopen_reference is not None:
            raise L5XExportError(
                "--base-library and --plcopen-reference apply only to "
                "--target automationml"
            )

        profile = _PROFILES[target]
        if compile_only:
            raise L5XExportError(
                "--compile-only applies only to --target openplc"
            )
        if schema_path is not None and profile is not PLCopenProfile.STANDARD_201:
            raise L5XExportError(
                "--xsd validates only the target-neutral PLCopen XML 2.01 "
                "target and cannot be used with --target codesys"
            )
        document = L5XParser().parse_document(source, report_mode=None)
        if not isinstance(document.target, Controller):
            raise L5XExportError(
                f"{target} export currently requires a Controller L5X target; "
                f"found {document.target_type.value}"
            )

        result = PLCopenExporter(profile).export(
            document.target,
            project_name=document.target_name,
        )
        if schema_path is not None:
            validate_plcopen_xml(result.xml, schema_path)

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.xml, encoding="utf-8")
    except L5XExportError:
        raise
    except (
        ET.ParseError,
        AutomationMLValidationError,
        AutomationMLValidationUnavailable,
        OSError,
        OpenPLCNativeUnsupportedError,
        PLCopenValidationError,
        PLCopenValidationUnavailable,
        ValueError,
    ) as error:
        raise L5XExportError(
            f"cannot export L5X '{source}' for target '{target}': {error}"
        ) from error

    label = (
        "PLCopen XML 2.01"
        if profile is PLCopenProfile.STANDARD_201
        else "CODESYS PLCopen XML"
    )
    stdout.write(f"Exported {label} to {destination}\n")
    for diagnostic in [*document.diagnostics, *result.diagnostics]:
        object_name = (
            f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        )
        stdout.write(
            f"{diagnostic.severity.value.upper()} {diagnostic.code}"
            f"{object_name}: {diagnostic.message}\n"
        )


def _export_automationml(
    source: Path,
    *,
    destination: Path,
    schema_path: Path | None,
    compile_only: bool,
    base_library_path: Path | None,
    plcopen_reference: Path | None,
    stdout: TextIO,
) -> None:
    """Write a semantically validated AutomationML 2.1 document."""
    if compile_only:
        raise L5XExportError(
            "--compile-only applies only to --target openplc"
        )
    if base_library_path is None:
        raise L5XExportError(
            "--base-library is required for --target automationml"
        )

    document = L5XParser().parse_document(source, report_mode=None)
    if not isinstance(document.target, Controller):
        raise L5XExportError(
            "automationml export currently requires a Controller L5X target; "
            f"found {document.target_type.value}"
        )
    destination_parent = destination.parent.resolve()
    base_reference = _relative_reference(
        base_library_path,
        destination_parent,
    )
    plcopen_path = (
        _relative_reference(plcopen_reference, destination_parent)
        if plcopen_reference is not None
        else None
    )
    result = AutomationMLExporter().export(
        document.target,
        project_name=document.target_name,
        plcopen_path=plcopen_path,
        base_library_path=base_reference,
        file_name=destination.name,
    )
    if schema_path is not None:
        validate_automationml_xml(result.xml, schema_path)
    validate_automationml_references(result.xml, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.xml, encoding="utf-8")

    stdout.write(f"Exported AutomationML 2.1 to {destination}\n")
    stdout.write(f"Base library reference: {base_reference}\n")
    if plcopen_path is not None:
        stdout.write(f"PLCopen document reference: {plcopen_path}\n")
    for diagnostic in document.diagnostics:
        object_name = (
            f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        )
        stdout.write(
            f"{diagnostic.severity.value.upper()} {diagnostic.code}"
            f"{object_name}: {diagnostic.message}\n"
        )


def _relative_reference(path: Path, destination_parent: Path) -> str:
    """Return a portable URI path from the AML directory to ``path``."""
    return os.path.relpath(path.resolve(), destination_parent).replace("\\", "/")


def _export_openplc_native(
    source: Path,
    *,
    destination: Path,
    schema_path: Path | None,
    compile_only: bool,
    stdout: TextIO,
) -> None:
    """Write the runtime-evidenced native OpenPLC project structure."""
    if schema_path is not None:
        raise L5XExportError(
            "--xsd applies only to --target plcopen; native OpenPLC output "
            "is a project directory, not one PLCopen XML document"
        )
    document = L5XParser().parse_document(source, report_mode=None)
    if not isinstance(document.target, Controller):
        raise L5XExportError(
            "openplc export currently requires a Controller L5X target; "
            f"found {document.target_type.value}"
        )
    result = OpenPLCNativeProjectExporter().export(
        document.target,
        destination=destination,
        project_name=document.target_name,
        compile_only=compile_only,
    )
    stdout.write(f"Exported native OpenPLC project to {result.destination}\n")
    stdout.write(
        f"Source program {result.source_program_name} was lowered as "
        f"{result.native_program_name}.\n"
    )
    for path in result.files:
        stdout.write(f"- {path}\n")
    for diagnostic in document.diagnostics:
        object_name = (
            f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        )
        stdout.write(
            f"{diagnostic.severity.value.upper()} {diagnostic.code}"
            f"{object_name}: {diagnostic.message}\n"
        )
