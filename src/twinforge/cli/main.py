"""Argument parsing and stable process exit codes for TwinForge."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from twinforge.discovery import (
    CipSoftwareInventoryCapability,
    DiscoveryStatePersistenceError,
)

from .cip_software import CipSoftwareCommandError, discover_cip_software
from .discovery_state import initialise_state, inspect_state, validate_state
from .diagnostics import ExitCode, write_json_diagnostic
from .l5x_export import L5XExportError, export_l5x_target
from .l5x_inspect import L5XInspectionError, inspect_l5x
from .l5x_report import L5XReportError, export_l5x_reports


def build_parser() -> argparse.ArgumentParser:
    """Build the public command tree without executing an operation."""
    parser = argparse.ArgumentParser(
        prog="twinforge",
        description="Vendor-neutral industrial automation engineering toolkit.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_l5x_command = commands.add_parser(
        "inspect",
        help="Inspect a Rockwell L5X document without changing it.",
    )
    inspect_l5x_command.add_argument("path", type=Path)
    inspect_l5x_command.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Summary output format (default: text).",
    )

    report_l5x_command = commands.add_parser(
        "report",
        help="Generate engineering reports from a Controller L5X document.",
    )
    report_l5x_command.add_argument("path", type=Path)
    report_l5x_command.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory in which to write the report bundle.",
    )

    export_l5x_command = commands.add_parser(
        "export",
        help="Export a Controller L5X document to a target format.",
    )
    export_l5x_command.add_argument("path", type=Path)
    export_l5x_command.add_argument(
        "--target",
        required=True,
        choices=("plcopen", "codesys", "openplc", "automationml"),
        help="Export target.",
    )
    export_l5x_command.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination file or project directory.",
    )
    export_l5x_command.add_argument(
        "--xsd",
        type=Path,
        help="Optional target-specific XSD used for validation.",
    )
    export_l5x_command.add_argument(
        "--compile-only",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override native OpenPLC compile-only mode.",
    )
    export_l5x_command.add_argument(
        "--config",
        type=Path,
        help="Versioned JSON target configuration file.",
    )
    export_l5x_command.add_argument(
        "--base-library",
        type=Path,
        help="AutomationML 2.1 base-library AML file.",
    )
    export_l5x_command.add_argument(
        "--plcopen-reference",
        type=Path,
        help="Optional PLCopen document referenced by AutomationML.",
    )
    export_l5x_command.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and plan the export without writing output.",
    )
    export_l5x_command.add_argument(
        "--diagnostics-format",
        choices=("text", "json"),
        default="text",
        help="Diagnostic output format (default: text).",
    )

    state = commands.add_parser(
        "state",
        help="Validate and inspect persisted discovery state.",
    )
    state_commands = state.add_subparsers(dest="state_command", required=True)

    initialise = state_commands.add_parser(
        "init",
        help="Create a new empty versioned state file.",
    )
    initialise.add_argument("path", type=Path)

    validate = state_commands.add_parser(
        "validate",
        help="Validate an existing state file.",
    )
    validate.add_argument("path", type=Path)

    inspect = state_commands.add_parser(
        "inspect",
        help="Display a validated state summary.",
    )
    inspect.add_argument("path", type=Path)
    inspect.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Summary output format (default: text).",
    )

    discover = commands.add_parser(
        "discover",
        help="Plan or execute explicitly authorized industrial discovery.",
    )
    discover_commands = discover.add_subparsers(
        dest="discover_command",
        required=True,
    )
    software = discover_commands.add_parser(
        "software",
        help="Plan structural Logix software inventory (dry-run by default).",
    )
    software.add_argument("address")
    software.add_argument(
        "--route-segment",
        action="append",
        required=True,
        help="Exact CIP route segment as PORT/LINK; repeat for each hop.",
    )
    software.add_argument("--authorization-reference", required=True)
    software.add_argument(
        "--capability",
        action="append",
        required=True,
        choices=tuple(item.value for item in CipSoftwareInventoryCapability),
    )
    software.add_argument("--maximum-requests", required=True, type=int)
    software.add_argument("--output", type=Path)
    software.add_argument(
        "--execute-experimental",
        action="store_true",
        help="Execute the unvalidated live adapter instead of writing a plan.",
    )
    software.add_argument("--confirmed-by")
    software.add_argument("--confirmed-at")
    software.add_argument("--laboratory-evidence-reference")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Execute one command and return a stable process exit code."""
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "inspect":
            inspect_l5x(
                arguments.path,
                output_format=arguments.format,
                stdout=output,
            )
        elif arguments.command == "report":
            export_l5x_reports(
                arguments.path,
                destination=arguments.output,
                stdout=output,
            )
        elif arguments.command == "export":
            export_l5x_target(
                arguments.path,
                target=arguments.target,
                destination=arguments.output,
                schema_path=arguments.xsd,
                compile_only=arguments.compile_only,
                config_path=arguments.config,
                base_library_path=arguments.base_library,
                plcopen_reference=arguments.plcopen_reference,
                dry_run=arguments.dry_run,
                diagnostics_format=arguments.diagnostics_format,
                stdout=output,
            )
        elif arguments.command == "discover":
            discover_cip_software(
                arguments.address,
                route_segments=tuple(arguments.route_segment),
                authorization_reference=arguments.authorization_reference,
                capability_names=tuple(arguments.capability),
                maximum_requests=arguments.maximum_requests,
                execute_experimental=arguments.execute_experimental,
                confirmed_by=arguments.confirmed_by,
                confirmed_at=arguments.confirmed_at,
                laboratory_evidence_reference=(
                    arguments.laboratory_evidence_reference
                ),
                destination=arguments.output,
                stdout=output,
            )
        elif arguments.state_command == "init":
            initialise_state(arguments.path, stdout=output)
        elif arguments.state_command == "validate":
            validate_state(arguments.path, stdout=output)
        else:
            inspect_state(
                arguments.path,
                output_format=arguments.format,
                stdout=output,
            )
    except L5XExportError as error:
        if arguments.diagnostics_format == "json":
            write_json_diagnostic(
                errors,
                status="error",
                operation="export",
                exit_code=error.exit_code,
                message=str(error),
                target=arguments.target,
                source=arguments.path,
                destination=arguments.output,
                dry_run=arguments.dry_run,
            )
        else:
            errors.write(f"error: {error}\n")
        return int(error.exit_code)
    except (
        DiscoveryStatePersistenceError,
        CipSoftwareCommandError,
        L5XInspectionError,
        L5XReportError,
    ) as error:
        errors.write(f"error: {error}\n")
        return 1
    return int(ExitCode.SUCCESS)
