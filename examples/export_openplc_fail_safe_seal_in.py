"""Generate a seal-in fixture for a physically NC, fail-safe stop circuit."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag, Task
from twinforge.targets.openplc import OpenPLCNativeProjectExporter


def build_controller() -> Controller:
    """Build a seal-in rung whose stop input is true only while healthy."""

    controller = Controller(name="OpenPLCFailSafeSealIn", identity=Identity())
    program = Program(name="PLC_PRG")
    for name in ("Start", "StopCircuitHealthy", "SystemActive"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(
            number=0,
            text=(
                "[XIC(Start),XIC(SystemActive)]"
                "XIC(StopCircuitHealthy)OTE(SystemActive);"
            ),
            comment="The physically NC stop circuit must remain energized and healthy.",
        )
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
    """Write a writable fixture that simulates the NC circuit's input state."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = OpenPLCNativeProjectExporter().export(
        build_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC Fail-Safe Seal-In",
        compile_only=True,
        locations={
            "Start": "%QX0.0",
            "StopCircuitHealthy": "%QX0.1",
            "SystemActive": "%QX0.2",
        },
    )
    print(f"Exported fail-safe native OpenPLC project to {result.destination}")


if __name__ == "__main__":
    main()
