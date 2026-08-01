"""Generate a native OpenPLC two-input parallel OR compatibility fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag, Task
from twinforge.targets.openplc import OpenPLCNativeProjectExporter


HARDWARE_LOCATIONS = {
    "LocalStart": "%IX0.0",
    "RemoteStart": "%IX0.1",
    "MotorRun": "%QX0.0",
}
SIMULATION_LOCATIONS = {
    "LocalStart": "%QX0.0",
    "RemoteStart": "%QX0.1",
    "MotorRun": "%QX0.2",
}


def build_or_controller() -> Controller:
    """Build an OR example with local and remote start paths."""

    controller = Controller(name="OpenPLCParallelOr", identity=Identity())
    program = Program(name="PLC_PRG")
    for name in ("LocalStart", "RemoteStart", "MotorRun"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(
            number=0,
            text="[XIC(LocalStart),XIC(RemoteStart)]OTE(MotorRun);",
            comment="Either local or remote Start runs the motor.",
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
    """Write the hardware-faithful or interactive simulation project."""

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
        build_or_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC Parallel OR",
        compile_only=True,
        locations=locations,
    )
    print(f"Exported native OpenPLC parallel-OR project to {result.destination}")


if __name__ == "__main__":
    main()
