"""Export one Structured Text AOI as a CODESYS PLCopen XML function block."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.exporters import (
    CodesysArgumentBinding,
    CodesysIRPLCopenExporter,
    CodesysProjectIntegration,
)
from twinforge.ir import (
    IRNormalizationPolicy,
    apply_aoi_execution_semantics,
    lower_add_on_instruction,
    normalize_reusable_unit,
)
from twinforge.parsers import L5XParser


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Lower one L5X Add-On Instruction to executable IR and export "
            "a CODESYS PLCopen XML POU."
        )
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Output XML file")
    parser.add_argument(
        "--aoi",
        help="AOI name; optional when the source contains exactly one AOI",
    )
    return parser.parse_args()


def main() -> int:
    """Run the evidence-backed AOI-to-CODESYS export pipeline."""

    args = _arguments()
    document = L5XParser().parse(args.source, report_mode=None)
    controller = next(document.iter_controllers())
    instructions = controller.add_on_instructions
    if args.aoi is None:
        if len(instructions) != 1:
            names = ", ".join(sorted(instructions))
            raise SystemExit(
                "specify --aoi because the source does not contain exactly "
                f"one AOI (available: {names or 'none'})"
            )
        instruction = next(iter(instructions.values()))
    else:
        try:
            instruction = instructions[args.aoi]
        except KeyError as error:
            names = ", ".join(sorted(instructions))
            raise SystemExit(
                f"AOI {args.aoi!r} was not found (available: "
                f"{names or 'none'})"
            ) from error

    analysis = analyze_structured_text_semantics(controller)
    unit = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in analysis.routines
            if finding.owner == f"AOI:{instruction.name}"
        },
    )
    normalized = normalize_reusable_unit(
        unit,
        IRNormalizationPolicy.PROMOTE_WRITTEN_INPUTS,
    )
    executable = apply_aoi_execution_semantics(normalized.unit)
    result = CodesysIRPLCopenExporter().export(
        executable,
        destination=args.destination,
        project_name=f"{instruction.name}_TwinForge",
        integration=CodesysProjectIntegration(
            instance_name="fbStrCapacity",
            bindings=(
                CodesysArgumentBinding(
                    "EnableIn",
                    "xEnable",
                    initial_value="TRUE",
                ),
                CodesysArgumentBinding("EnableOut", "xEnableOut"),
                CodesysArgumentBinding(
                    "Ref_Data",
                    "aData",
                    dimensions="10",
                ),
                CodesysArgumentBinding("Val", "diCapacity"),
            ),
        ),
    )

    print(f"Wrote {args.destination}")
    for diagnostic in result.diagnostics:
        print(f"{diagnostic.code}: {diagnostic.message}")
    if result.requirements:
        values = ", ".join(item.value for item in result.requirements)
        print(f"Unresolved target requirements: {values}")
    return 0 if result.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
