"""Export a PowerFlex functional description from related L5X evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.analysis import (
    analyze_cyclic_io_contract,
    build_device_diagnostic_report,
    build_device_functional_description,
)
from twinforge.assembly import assemble_corpus_devices
from twinforge.exporters import FunctionalDescriptionMarkdownExporter
from twinforge.model import AddOnInstruction
from twinforge.parsers.l5x import L5XCorpusParser, L5XParser


def export_functional_description(
    source: Path,
    destination: Path,
) -> None:
    """Assemble related evidence and write the functional description."""

    corpus = L5XCorpusParser().parse_directory(source)
    devices = assemble_corpus_devices(corpus)
    if len(devices) != 1:
        raise ValueError(
            "functional description requires exactly one assembled device"
        )
    plant = L5XParser().parse(source / "Dvc_PF525_AOI.L5X", report_mode=None)
    controller = plant.controllers[0]
    implementation = controller.add_on_instructions.get("Dvc_PF525")
    if not isinstance(implementation, AddOnInstruction):
        raise ValueError("Dvc_PF525 AOI was not found")
    module = devices[0].source.modules[0]
    connection = module.connections[0] if module.connections else None
    cyclic = analyze_cyclic_io_contract(
        controller,
        implementation,
        connection,
    )
    supporting = tuple(
        item
        for name, item in controller.add_on_instructions.items()
        if name != implementation.name
    )
    diagnostics = build_device_diagnostic_report(
        devices[0].device,
        implementation,
        supporting_implementations=supporting,
    )
    report = build_device_functional_description(
        devices[0].device,
        implementation,
        cyclic,
        diagnostics,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        FunctionalDescriptionMarkdownExporter().export(report),
        encoding="utf-8",
    )


def main() -> None:
    """Parse command-line arguments and export the description."""

    parser = argparse.ArgumentParser(
        description="Export a device functional description."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export_functional_description(args.source, args.destination)
    print(f"Exported functional description to {args.destination}")


if __name__ == "__main__":
    main()
