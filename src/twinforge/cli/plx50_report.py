"""Installed command adapter for PLX50 multi-source mapping reports."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TextIO

from twinforge.assembly import (
    apply_plx50_gateway_configuration,
    apply_plx50_logix_mapping,
    assemble_gateway_descriptions,
    plx50_logix_mapping_json,
)
from twinforge.exporters import Plx50LogixMappingMarkdownExporter
from twinforge.exporters import AutomationMLExporter
from twinforge.parsers import EDSParser, GSDParser, L5XParser, PLX50PSJParser


class Plx50ReportError(RuntimeError):
    """Raised when a PLX50 report cannot be generated or written."""


def export_plx50_mapping_report(
    *,
    eds_source: Path,
    gsd_source: Path,
    configuration_source: Path,
    mapping_source: Path,
    destination: Path,
    stdout: TextIO,
    base_library_path: Path | None = None,
) -> tuple[Path, ...]:
    """Correlate four source formats and write human and machine reports."""

    try:
        eds = EDSParser().parse(eds_source)
        gsd = GSDParser().parse(gsd_source)
        project = PLX50PSJParser().parse(configuration_source)
        if len(project.devices) != 1:
            raise Plx50ReportError(
                "PLX50 report currently requires exactly one configured "
                f"gateway; found {len(project.devices)}"
            )
        configuration = project.devices[0]
        if configuration.primary_interface != "EtherNetIP":
            raise Plx50ReportError(
                "generated Logix mapping correlation requires an "
                "EtherNetIP primary interface; found "
                f"{configuration.primary_interface!r}"
            )
        plant = L5XParser().parse(mapping_source, report_mode=None)
        controllers = tuple(plant.iter_controllers())
        if len(controllers) != 1:
            raise Plx50ReportError(
                "generated Logix mapping must resolve to exactly one "
                f"controller context; found {len(controllers)}"
            )

        gateway = assemble_gateway_descriptions(eds, gsd).gateway
        apply_plx50_gateway_configuration(gateway, configuration)
        result = apply_plx50_logix_mapping(
            gateway,
            configuration,
            controllers[0],
        )
        report = Plx50LogixMappingMarkdownExporter().export(
            result,
            title=f"{gateway.name} Logix mapping",
        )
        destination.mkdir(parents=True, exist_ok=True)
        report_path = destination / "plx50_logix_mapping.md"
        report_path.write_text(report, encoding="utf-8")
        json_path = destination / "plx50_logix_mapping.json"
        json_path.write_text(
            plx50_logix_mapping_json(result),
            encoding="utf-8",
        )
        generated_paths = [report_path, json_path]
        if base_library_path is not None:
            automationml_path = destination / "plx50_gateway.aml"
            AutomationMLExporter().export(
                controllers[0],
                project_name=f"{gateway.name} communication model",
                base_library_path=base_library_path,
                destination=automationml_path,
                gateways=(gateway,),
            )
            generated_paths.append(automationml_path)
    except Plx50ReportError:
        raise
    except (ET.ParseError, OSError, UnicodeError, ValueError) as error:
        raise Plx50ReportError(
            f"cannot generate PLX50 mapping report: {error}"
        ) from error

    output_paths = "".join(f"- {path}\n" for path in generated_paths)
    stdout.write(
        f"Exported PLX50 mapping reports to {destination}\n"
        f"{output_paths}"
        f"- Correlated points: {len(result.correlations)}\n"
        f"- Unresolved points: {len(result.unresolved_points)}\n"
        f"- Diagnostics: {len(result.diagnostics)}\n"
    )
    return tuple(generated_paths)
