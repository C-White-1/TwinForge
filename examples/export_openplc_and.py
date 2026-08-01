"""Generate a native OpenPLC two-input serial AND compatibility fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag, Task
from twinforge.targets.openplc import OpenPLCNativeProjectExporter


HARDWARE_LOCATIONS = {
    "GuardClosed": "%IX0.0",
    "Start": "%IX0.1",
    "MotorRun": "%QX0.0",
}
SIMULATION_LOCATIONS = {
    "GuardClosed": "%QX0.0",
    "Start": "%QX0.1",
    "MotorRun": "%QX0.2",
}


def build_and_controller() -> Controller:
    """Build a guarded-start example with two located inputs and one output."""

    controller = Controller(name="OpenPLCSerialAnd", identity=Identity())
    program = Program(name="PLC_PRG")
    for name in ("GuardClosed", "Start", "MotorRun"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(
            number=0,
            text="XIC(GuardClosed)XIC(Start)OTE(MotorRun);",
            comment="Motor runs only when the guard is closed and Start is true.",
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
    """Write the native OpenPLC compatibility project."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Use writable %QX points for the two simulated input conditions",
    )
    args = parser.parse_args()
    locations = SIMULATION_LOCATIONS if args.simulation else HARDWARE_LOCATIONS
    result = OpenPLCNativeProjectExporter().export(
        build_and_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC Serial AND",
        compile_only=True,
        locations=locations,
    )
    print(f"Exported native OpenPLC serial-AND project to {result.destination}")


if __name__ == "__main__":
    main()
