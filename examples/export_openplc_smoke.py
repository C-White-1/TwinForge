"""Generate a minimal, deterministic OpenPLC import/runtime smoke fixture."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
    Program,
    Routine,
    Tag,
    Task,
)
from twinforge.exporters import (
    PLCopenValidationUnavailable,
    validate_plcopen_xml,
)
from twinforge.targets.openplc import (
    OpenPLCExporter,
    OpenPLCNativeProjectExporter,
)


FIXTURE_TIME = datetime(2026, 7, 30, tzinfo=timezone.utc)


def build_smoke_controller() -> Controller:
    """Build a two-tag ladder program with one periodic task."""

    controller = Controller(name="OpenPLCSmoke", identity=Identity())

    program = Program(name="PLC_PRG")
    program.add_tag(Tag(name="Enable", data_type="BOOL"))
    program.add_tag(Tag(name="Output", data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(number=0, text="XIC(Enable)OTE(Output);")
    )
    program.add_routine(routine)
    controller.add_program(program)
    controller.add_task(
        Task(
            name="MainTask",
            task_type="Periodic",
            rate=20,
            priority=1,
            scheduled_program_names=[program.name],
            scheduled_programs=[program],
        )
    )
    return controller


def main() -> None:
    """Write the stable smoke-test document."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--xsd",
        type=Path,
        help="Optional PLCopen 2.01 XSD used to validate the fixture",
    )
    parser.add_argument(
        "--native-destination",
        type=Path,
        help="Optional destination for the native OpenPLC project directory",
    )
    args = parser.parse_args()

    result = OpenPLCExporter().export(
        build_smoke_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC Smoke Test",
        creation_time=FIXTURE_TIME,
    )
    if args.xsd:
        try:
            validate_plcopen_xml(result.xml, args.xsd)
        except PLCopenValidationUnavailable as error:
            raise SystemExit(str(error)) from error
        print(f"Validated fixture against {args.xsd}")

    print(f"Exported OpenPLC smoke fixture to {args.destination}")
    if args.native_destination:
        native = OpenPLCNativeProjectExporter().export(
            build_smoke_controller(),
            destination=args.native_destination,
            project_name="TwinForge OpenPLC Smoke Test",
            compile_only=True,
            locations={"Enable": "%QX0.0", "Output": "%QX0.1"},
        )
        print(f"Exported native OpenPLC project to {native.destination}")
    for diagnostic in result.diagnostics:
        print(f"{diagnostic.severity.value.upper()} {diagnostic.code}: {diagnostic.message}")


if __name__ == "__main__":
    main()
