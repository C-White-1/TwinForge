"""Installed adapters for exporting L5X models to target formats."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import os
from pathlib import Path
from typing import Any, TextIO

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

from .export_config import OpenPLCExportConfig, load_openplc_export_config
from .diagnostics import ExitCode, write_json_diagnostic


class L5XExportError(RuntimeError):
    """Raised when an installed L5X export operation cannot complete."""

    def __init__(
        self,
        message: str,
        *,
        exit_code: ExitCode = ExitCode.INVALID_INPUT,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code


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
    compile_only: bool | None,
    config_path: Path | None,
    base_library_path: Path | None,
    plcopen_reference: Path | None,
    dry_run: bool,
    diagnostics_format: str,
    stdout: TextIO,
) -> None:
    """Export a Controller L5X using one explicit target adapter."""
    try:
        _require_input_file(source, "L5X source")
        if target == "openplc":
            config = (
                load_openplc_export_config(config_path)
                if config_path is not None
                else OpenPLCExportConfig(
                    schema_version="1.0",
                    target="openplc",
                )
            )
            _export_openplc_native(
                source,
                destination=destination,
                schema_path=schema_path,
                compile_only=(
                    compile_only
                    if compile_only is not None
                    else config.compile_only
                ),
                config=config,
                dry_run=dry_run,
                diagnostics_format=diagnostics_format,
                stdout=stdout,
            )
            return
        if config_path is not None:
            raise L5XExportError(
                "--config currently applies only to --target openplc"
            )
        if target == "automationml":
            _export_automationml(
                source,
                destination=destination,
                schema_path=schema_path,
                compile_only=compile_only,
                base_library_path=base_library_path,
                plcopen_reference=plcopen_reference,
                dry_run=dry_run,
                diagnostics_format=diagnostics_format,
                stdout=stdout,
            )
            return

        if base_library_path is not None or plcopen_reference is not None:
            raise L5XExportError(
                "--base-library and --plcopen-reference apply only to "
                "--target automationml"
            )

        profile = _PROFILES[target]
        if compile_only is not None:
            raise L5XExportError(
                "--compile-only applies only to --target openplc"
            )
        if schema_path is not None and profile is not PLCopenProfile.STANDARD_201:
            raise L5XExportError(
                "--xsd validates only the target-neutral PLCopen XML 2.01 "
                "target and cannot be used with --target codesys"
            )
        if schema_path is not None:
            _require_input_file(schema_path, "--xsd")
        document = L5XParser().parse_document(source, report_mode=None)
        if not isinstance(document.target, Controller):
            raise L5XExportError(
                f"{target} export currently requires a Controller L5X target; "
                f"found {document.target_type.value}",
                exit_code=ExitCode.UNSUPPORTED,
            )

        result = PLCopenExporter(profile).export(
            document.target,
            project_name=document.target_name,
        )
        if schema_path is not None:
            validate_plcopen_xml(result.xml, schema_path)

        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(result.xml, encoding="utf-8")
    except L5XExportError:
        raise
    except (AutomationMLValidationError, PLCopenValidationError) as error:
        raise L5XExportError(
            f"cannot validate L5X export '{source}' for target '{target}': "
            f"{error}",
            exit_code=ExitCode.VALIDATION_FAILED,
        ) from error
    except (OpenPLCNativeUnsupportedError,) as error:
        raise L5XExportError(
            f"cannot export L5X '{source}' for target '{target}': {error}",
            exit_code=ExitCode.UNSUPPORTED,
        ) from error
    except (
        AutomationMLValidationUnavailable,
        OSError,
        PLCopenValidationUnavailable,
    ) as error:
        raise L5XExportError(
            f"cannot complete L5X export '{source}' for target '{target}': "
            f"{error}",
            exit_code=ExitCode.OPERATION_FAILED,
        ) from error
    except (
        ET.ParseError,
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
    verb = "Ready to export" if dry_run else "Exported"
    diagnostics = [*document.diagnostics, *result.diagnostics]
    if diagnostics_format == "json":
        write_json_diagnostic(
            stdout,
            status="ready" if dry_run else "exported",
            operation="export",
            exit_code=ExitCode.SUCCESS,
            message=f"{verb} {label} to {destination}",
            target=target,
            source=source,
            destination=destination,
            dry_run=dry_run,
            outputs=(destination,),
            diagnostics=tuple(_diagnostic_value(item) for item in diagnostics),
        )
        return
    stdout.write(f"{verb} {label} to {destination}\n")
    for diagnostic in diagnostics:
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
    compile_only: bool | None,
    base_library_path: Path | None,
    plcopen_reference: Path | None,
    dry_run: bool,
    diagnostics_format: str,
    stdout: TextIO,
) -> None:
    """Write a semantically validated AutomationML 2.1 document."""
    if compile_only is not None:
        raise L5XExportError(
            "--compile-only applies only to --target openplc"
        )
    if base_library_path is None:
        raise L5XExportError(
            "--base-library is required for --target automationml"
        )
    _require_input_file(base_library_path, "--base-library")
    if schema_path is not None:
        _require_input_file(schema_path, "--xsd")
    if plcopen_reference is not None:
        _require_input_file(plcopen_reference, "--plcopen-reference")

    document = L5XParser().parse_document(source, report_mode=None)
    if not isinstance(document.target, Controller):
        raise L5XExportError(
            "automationml export currently requires a Controller L5X target; "
            f"found {document.target_type.value}",
            exit_code=ExitCode.UNSUPPORTED,
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
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.xml, encoding="utf-8")

    verb = "Ready to export" if dry_run else "Exported"
    message = f"{verb} AutomationML 2.1 to {destination}"
    if diagnostics_format == "json":
        write_json_diagnostic(
            stdout,
            status="ready" if dry_run else "exported",
            operation="export",
            exit_code=ExitCode.SUCCESS,
            message=message,
            target="automationml",
            source=source,
            destination=destination,
            dry_run=dry_run,
            outputs=(destination,),
            diagnostics=tuple(
                _diagnostic_value(item) for item in document.diagnostics
            ),
        )
        return
    stdout.write(message + "\n")
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
    """Return a portable relative path, or an absolute cross-volume path."""
    resolved = path.resolve()
    try:
        return os.path.relpath(resolved, destination_parent).replace("\\", "/")
    except ValueError:
        # Windows cannot express a relative path between different drives.
        return resolved.as_posix()


def _require_input_file(path: Path, option: str) -> None:
    """Reject a missing or non-file input before conversion work begins."""
    if not path.is_file():
        raise L5XExportError(
            f"{option} file does not exist or is not a file: {path}",
            exit_code=ExitCode.INVALID_INPUT,
        )


def _export_openplc_native(
    source: Path,
    *,
    destination: Path,
    schema_path: Path | None,
    compile_only: bool,
    config: OpenPLCExportConfig,
    dry_run: bool,
    diagnostics_format: str,
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
            f"found {document.target_type.value}",
            exit_code=ExitCode.UNSUPPORTED,
    )
    exporter = OpenPLCNativeProjectExporter()
    plan = exporter.plan(
        document.target,
        project_name=document.target_name,
        compile_only=compile_only,
        locations=config.locations,
        timer_elapsed_locations=config.timer_elapsed_locations,
        counter_accumulator_locations=config.counter_accumulator_locations,
        counter_status_locations=config.counter_status_locations,
    )
    if dry_run:
        files = tuple(destination / path for path in plan.documents)
    else:
        result = exporter.export(
            document.target,
            destination=destination,
            project_name=document.target_name,
            compile_only=compile_only,
            locations=config.locations,
            timer_elapsed_locations=config.timer_elapsed_locations,
            counter_accumulator_locations=(
                config.counter_accumulator_locations
            ),
            counter_status_locations=config.counter_status_locations,
        )
        files = result.files
    verb = "Ready to export" if dry_run else "Exported"
    message = f"{verb} native OpenPLC project to {destination}"
    if diagnostics_format == "json":
        write_json_diagnostic(
            stdout,
            status="ready" if dry_run else "exported",
            operation="export",
            exit_code=ExitCode.SUCCESS,
            message=message,
            target="openplc",
            source=source,
            destination=destination,
            dry_run=dry_run,
            outputs=tuple(files),
            diagnostics=tuple(
                _diagnostic_value(item) for item in document.diagnostics
            ),
        )
        return
    stdout.write(message + "\n")
    stdout.write(
        f"Source program {plan.source_program_name} was lowered as "
        f"{plan.native_program_name}.\n"
    )
    for path in files:
        stdout.write(f"- {path}\n")
    for diagnostic in document.diagnostics:
        object_name = (
            f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        )
        stdout.write(
            f"{diagnostic.severity.value.upper()} {diagnostic.code}"
            f"{object_name}: {diagnostic.message}\n"
        )


def _diagnostic_value(diagnostic: Any) -> dict[str, str | None]:
    """Convert parser/exporter diagnostics to the stable CLI representation."""
    severity = diagnostic.severity.value
    return {
        "severity": severity,
        "code": diagnostic.code,
        "object_name": diagnostic.object_name,
        "message": diagnostic.message,
    }
