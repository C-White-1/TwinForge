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
    SnmpConversionError,
)

from .cip_identity import CipIdentityCommandError, discover_cip_identity
from .cip_software import CipSoftwareCommandError, discover_cip_software
from .codesys_deployment import (
    CodesysDeploymentCommandError,
    export_codesys_powerflex525_bundle,
)
from .communication_graph import (
    CommunicationGraphCommandError,
    export_communication_graph,
)
from .discovery_state import initialise_state, inspect_state, validate_state
from .discovery_fake import FakeSnapshotCommandError, generate_fake_snapshot
from .diagnostics import ExitCode, write_json_diagnostic
from .l5x_export import L5XExportError, export_l5x_target
from .l5x_inspect import L5XInspectionError, inspect_l5x
from .l5x_report import L5XReportError, export_l5x_reports
from .model_json import (
    compare_model_json_files,
    ModelJSONCommandError,
    export_model_json_schema,
    inspect_model_json_file,
    list_model_json_records,
    query_model_json_file,
    validate_model_json_file,
)
from .plx50_report import Plx50ReportError, export_plx50_mapping_report
from .review_schema import ReviewSchemaCommandError, export_review_schema
from .review_validation import (
    ReviewValidationCommandError,
    validate_review_document,
)
from .report_bundle import (
    ReportBundleCommandError,
    export_report_manifest_schema,
    verify_report_bundle,
)
from .snmp_conversion import convert_walk_command


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
    report_l5x_command.add_argument(
        "--alarm-review",
        type=Path,
        help="Optional versioned JSON alarm/trip engineering review overlay.",
    )
    report_l5x_command.add_argument(
        "--cause-effect-review",
        type=Path,
        help="Optional versioned JSON cause-and-effect engineering review overlay.",
    )

    export_l5x_command = commands.add_parser(
        "export",
        help="Export a Controller L5X document to a target format.",
    )
    export_l5x_command.add_argument("path", type=Path)
    export_l5x_command.add_argument(
        "--target",
        required=True,
        choices=("plcopen", "codesys", "openplc", "automationml", "json"),
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

    codesys = commands.add_parser(
        "codesys",
        help="Build validated native CODESYS deployment artifacts.",
    )
    codesys_commands = codesys.add_subparsers(
        dest="codesys_command",
        required=True,
    )
    codesys_bundle = codesys_commands.add_parser(
        "bundle",
        help="Build a PowerFlex 525 deployment bundle from a JSON manifest.",
    )
    codesys_bundle.add_argument("manifest", type=Path)
    codesys_bundle.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory in which to write the deployment bundle.",
    )

    model = commands.add_parser(
        "model",
        help="Validate and inspect neutral TwinForge model artifacts.",
    )
    model_commands = model.add_subparsers(
        dest="model_command",
        required=True,
    )
    model_validate = model_commands.add_parser(
        "validate",
        help="Validate a versioned neutral-model JSON document.",
    )
    model_validate.add_argument("path", type=Path)
    model_inspect = model_commands.add_parser(
        "inspect",
        help="Inventory a validated neutral-model JSON document.",
    )
    model_inspect.add_argument("path", type=Path)
    model_inspect.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Inventory output format (default: text).",
    )
    model_schema = model_commands.add_parser(
        "schema",
        help="Export the maintained neutral-model JSON Schema.",
    )
    model_schema.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination for the JSON Schema file.",
    )
    model_query = model_commands.add_parser(
        "query",
        help="Select validated model evidence with an RFC 6901 JSON Pointer.",
    )
    model_query.add_argument("path", type=Path)
    model_query.add_argument(
        "pointer",
        help="Fragment-form JSON Pointer, such as '#/document/target'.",
    )
    model_query.add_argument(
        "--resolve-reference",
        action="store_true",
        help="Resolve the selected node when it is exactly a $ref object.",
    )
    model_query.add_argument(
        "--compact",
        action="store_true",
        help="Write compact rather than indented JSON.",
    )
    model_records = model_commands.add_parser(
        "records",
        help="List typed model records and their stable JSON Pointers.",
    )
    model_records.add_argument("path", type=Path)
    model_records.add_argument(
        "--type",
        dest="record_type",
        help="Exact short or fully qualified $type to include.",
    )
    model_records.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Record-list output format (default: text).",
    )
    model_compare = model_commands.add_parser(
        "compare",
        help="Compare two validated neutral-model JSON documents.",
    )
    model_compare.add_argument("before", type=Path)
    model_compare.add_argument("after", type=Path)
    model_compare.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Comparison output format (default: text).",
    )

    review = commands.add_parser(
        "review",
        help="Export contracts for attributable engineering-review inputs.",
    )
    review_commands = review.add_subparsers(
        dest="review_command",
        required=True,
    )
    review_schema = review_commands.add_parser(
        "schema",
        help="Export an installed engineering-review JSON Schema.",
    )
    review_schema.add_argument(
        "kind",
        choices=("alarm", "cause-effect", "coverage"),
        help="Review contract to export.",
    )
    review_schema.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination for the JSON Schema file.",
    )
    review_validate = review_commands.add_parser(
        "validate",
        help="Validate an engineering-review input document.",
    )
    review_validate.add_argument(
        "kind",
        choices=("alarm", "cause-effect"),
        help="Review input contract to validate.",
    )
    review_validate.add_argument("path", type=Path)
    review_validate.add_argument(
        "--source",
        type=Path,
        help="Optional Controller L5X used to reconcile reviewed keys.",
    )

    reports = commands.add_parser(
        "reports",
        help="Verify generated engineering-report bundles.",
    )
    reports_commands = reports.add_subparsers(
        dest="reports_command",
        required=True,
    )
    reports_verify = reports_commands.add_parser(
        "verify",
        help="Verify a report manifest against all source and report bytes.",
    )
    reports_verify.add_argument("directory", type=Path)
    reports_verify.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Original L5X input recorded by the manifest.",
    )
    reports_verify.add_argument("--alarm-review", type=Path)
    reports_verify.add_argument("--cause-effect-review", type=Path)
    reports_schema = reports_commands.add_parser(
        "schema",
        help="Export the installed engineering-report manifest JSON Schema.",
    )
    reports_schema.add_argument("--output", required=True, type=Path)

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
    fake_snapshot = discover_commands.add_parser(
        "fake-snapshot",
        help="Generate a sanitized Discovery Snapshot without network I/O.",
    )
    fake_snapshot.add_argument("--engagement", required=True)
    fake_snapshot.add_argument("--authorization-reference", required=True)
    fake_snapshot.add_argument(
        "--captured-at",
        required=True,
        help="Timezone-qualified ISO 8601 capture time.",
    )
    fake_snapshot.add_argument("--output", type=Path)
    identity = discover_commands.add_parser(
        "identity",
        help="Plan a bounded CIP Identity read (dry-run by default).",
    )
    identity.add_argument("address")
    identity.add_argument("--engagement", required=True)
    identity.add_argument("--authorization-reference", required=True)
    identity.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Request timeout in seconds, greater than 0 and at most 10.",
    )
    identity.add_argument("--output", type=Path)
    identity.add_argument(
        "--execute",
        action="store_true",
        help="Confirm the single live request; otherwise emit only a plan.",
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
    software.add_argument("--engagement", required=True)
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

    snmp = commands.add_parser(
        "snmp",
        help="Plan or execute offline SNMP evidence workflows.",
    )
    snmp_commands = snmp.add_subparsers(dest="snmp_command", required=True)
    convert_walk = snmp_commands.add_parser(
        "convert-walk",
        help="Convert explicitly declared Net-SNMP walk text to SNMPSim format.",
    )
    convert_walk.add_argument("input", type=Path)
    convert_walk.add_argument("--output", required=True, type=Path)
    convert_walk.add_argument("--expected-sha256", required=True)
    convert_walk.add_argument("--source-url", required=True)
    convert_walk.add_argument("--license", required=True)
    convert_walk.add_argument("--device-category", required=True)
    convert_walk.add_argument(
        "--sanitized", action=argparse.BooleanOptionalAction, required=True
    )
    convert_walk.add_argument("--approved-by", required=True)
    convert_walk.add_argument("--approved-at", required=True)
    convert_walk.add_argument("--rationale", required=True)
    convert_walk.add_argument("--max-input-bytes", type=int, default=16 * 1024 * 1024)
    convert_walk.add_argument("--reject-unparsed-lines", action="store_true")
    convert_walk.add_argument(
        "--execute",
        action="store_true",
        help="Write conversion outputs; otherwise print the dry-run plan.",
    )

    gateway = commands.add_parser(
        "gateway",
        help="Correlate offline multi-protocol gateway evidence.",
    )
    gateway_commands = gateway.add_subparsers(
        dest="gateway_command",
        required=True,
    )
    plx50_report = gateway_commands.add_parser(
        "report",
        help="Generate a PLX50 PROFIBUS-to-Logix mapping report.",
    )
    plx50_report.add_argument("--eds", required=True, type=Path)
    plx50_report.add_argument("--gsd", required=True, type=Path)
    plx50_report.add_argument("--config", required=True, type=Path)
    plx50_report.add_argument("--mapping", required=True, type=Path)
    plx50_report.add_argument("--output", required=True, type=Path)
    plx50_report.add_argument(
        "--base-library",
        type=Path,
        help=(
            "Optional AutomationML 2.1 base library; when supplied, also "
            "write the gateway communication model."
        ),
    )
    communication = commands.add_parser(
        "communication",
        help="Build evidence-backed communication models.",
    )
    communication_commands = communication.add_subparsers(
        dest="communication_command",
        required=True,
    )
    graph = communication_commands.add_parser(
        "graph",
        help="Build a multi-controller graph from an L5X corpus.",
    )
    graph.add_argument("source", type=Path)
    graph.add_argument("--output", required=True, type=Path)
    graph.add_argument(
        "--bindings",
        type=Path,
        help="Optional versioned JSON file of explicit message bindings.",
    )
    graph.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Search the corpus directory recursively (default: true).",
    )
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
                alarm_review_path=arguments.alarm_review,
                cause_effect_review_path=arguments.cause_effect_review,
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
        elif arguments.command == "codesys":
            export_codesys_powerflex525_bundle(
                arguments.manifest,
                arguments.output,
                stdout=output,
            )
        elif arguments.command == "model":
            if arguments.model_command == "validate":
                validate_model_json_file(arguments.path, stdout=output)
            elif arguments.model_command == "inspect":
                inspect_model_json_file(
                    arguments.path,
                    output_format=arguments.format,
                    stdout=output,
                )
            elif arguments.model_command == "schema":
                export_model_json_schema(arguments.output, stdout=output)
            elif arguments.model_command == "query":
                query_model_json_file(
                    arguments.path,
                    arguments.pointer,
                    resolve_reference=arguments.resolve_reference,
                    compact=arguments.compact,
                    stdout=output,
                )
            elif arguments.model_command == "records":
                list_model_json_records(
                    arguments.path,
                    record_type=arguments.record_type,
                    output_format=arguments.format,
                    stdout=output,
                )
            else:
                compare_model_json_files(
                    arguments.before,
                    arguments.after,
                    output_format=arguments.format,
                    stdout=output,
                )
        elif arguments.command == "review":
            if arguments.review_command == "schema":
                export_review_schema(
                    arguments.kind,
                    arguments.output,
                    stdout=output,
                )
            else:
                validate_review_document(
                    arguments.kind,
                    arguments.path,
                    l5x_source=arguments.source,
                    stdout=output,
                )
        elif arguments.command == "reports":
            if arguments.reports_command == "schema":
                export_report_manifest_schema(arguments.output, stdout=output)
            else:
                verify_report_bundle(
                    arguments.directory,
                    source=arguments.source,
                    alarm_review=arguments.alarm_review,
                    cause_effect_review=arguments.cause_effect_review,
                    stdout=output,
                )
        elif arguments.command == "discover":
            if arguments.discover_command == "fake-snapshot":
                generate_fake_snapshot(
                    engagement=arguments.engagement,
                    authorization_reference=arguments.authorization_reference,
                    captured_at=arguments.captured_at,
                    destination=arguments.output,
                    stdout=output,
                )
            elif arguments.discover_command == "identity":
                discover_cip_identity(
                    arguments.address,
                    engagement=arguments.engagement,
                    authorization_reference=arguments.authorization_reference,
                    timeout=arguments.timeout,
                    execute=arguments.execute,
                    destination=arguments.output,
                    stdout=output,
                )
            else:
                discover_cip_software(
                    arguments.address,
                    route_segments=tuple(arguments.route_segment),
                    engagement=arguments.engagement,
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
        elif arguments.command == "snmp":
            convert_walk_command(
                arguments.input,
                arguments.output,
                expected_sha256=arguments.expected_sha256,
                source_url=arguments.source_url,
                license_name=arguments.license,
                device_category=arguments.device_category,
                sanitized=arguments.sanitized,
                approved_by=arguments.approved_by,
                approved_at=arguments.approved_at,
                rationale=arguments.rationale,
                max_input_bytes=arguments.max_input_bytes,
                allow_unparsed_lines=not arguments.reject_unparsed_lines,
                execute=arguments.execute,
                stdout=output,
            )
        elif arguments.command == "gateway":
            export_plx50_mapping_report(
                eds_source=arguments.eds,
                gsd_source=arguments.gsd,
                configuration_source=arguments.config,
                mapping_source=arguments.mapping,
                destination=arguments.output,
                stdout=output,
                base_library_path=arguments.base_library,
            )
        elif arguments.command == "communication":
            export_communication_graph(
                arguments.source,
                arguments.output,
                bindings_source=arguments.bindings,
                recursive=arguments.recursive,
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
        FakeSnapshotCommandError,
        CipIdentityCommandError,
        CipSoftwareCommandError,
        SnmpConversionError,
        L5XInspectionError,
        L5XReportError,
        Plx50ReportError,
        CommunicationGraphCommandError,
        CodesysDeploymentCommandError,
        ModelJSONCommandError,
        ReviewSchemaCommandError,
        ReviewValidationCommandError,
        ReportBundleCommandError,
    ) as error:
        errors.write(f"error: {error}\n")
        return 1
    return int(ExitCode.SUCCESS)
