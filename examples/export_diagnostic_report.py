"""Export a diagnostic and fault report from a related L5X corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.analysis import build_device_diagnostic_report
from twinforge.assembly import assemble_corpus_devices
from twinforge.exporters import DeviceDiagnosticMarkdownExporter
from twinforge.model import AddOnInstruction
from twinforge.parsers.l5x import L5XCorpusParser, L5XParser


def export_diagnostic_report(source: Path, destination: Path) -> None:
    """Assemble the PowerFlex device and write its diagnostic report."""

    corpus = L5XCorpusParser().parse_directory(source)
    devices = assemble_corpus_devices(corpus)
    if len(devices) != 1:
        raise ValueError(
            "diagnostic export requires exactly one assembled device"
        )
    aoi_path = source / "Dvc_PF525_AOI.L5X"
    plant = L5XParser().parse(aoi_path, report_mode=None)
    controller = plant.controllers[0]
    implementation = controller.add_on_instructions.get("Dvc_PF525")
    if not isinstance(implementation, AddOnInstruction):
        raise ValueError("Dvc_PF525 AOI was not found")
    supporting = tuple(
        item
        for name, item in controller.add_on_instructions.items()
        if name != implementation.name
    )
    report = build_device_diagnostic_report(
        devices[0].device,
        implementation,
        supporting_implementations=supporting,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        DeviceDiagnosticMarkdownExporter().export(report),
        encoding="utf-8",
    )


def main() -> None:
    """Parse command-line arguments and export the report."""

    parser = argparse.ArgumentParser(
        description="Export device diagnostic and fault evidence."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export_diagnostic_report(args.source, args.destination)
    print(f"Exported diagnostic report to {args.destination}")


if __name__ == "__main__":
    main()
