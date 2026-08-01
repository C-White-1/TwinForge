"""Generate a native OpenPLC start/stop seal-in compatibility fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag, Task
from twinforge.targets.openplc import OpenPLCNativeProjectExporter


HARDWARE_LOCATIONS = {
    "Start": "%IX0.0",
    "StopPressed": "%IX0.1",
    "SystemActive": "%QX0.0",
}
SIMULATION_LOCATIONS = {
    "Start": "%QX0.0",
    "StopPressed": "%QX0.1",
    "SystemActive": "%QX0.2",
}


def build_seal_in_controller() -> Controller:
    """Build a stop/start circuit held by its energized output state."""

    controller = Controller(name="OpenPLCSealIn", identity=Identity())
    program = Program(name="PLC_PRG")
    for name in ("Start", "StopPressed", "SystemActive"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(
            number=0,
            text=(
                "[XIC(Start),XIC(SystemActive)]"
                "XIO(StopPressed)OTE(SystemActive);"
            ),
            comment="Start seals in SystemActive until StopPressed is true.",
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
        help="Use writable %QX points for simulated Start and StopPressed",
    )
    args = parser.parse_args()
    locations = SIMULATION_LOCATIONS if args.simulation else HARDWARE_LOCATIONS
    result = OpenPLCNativeProjectExporter().export(
        build_seal_in_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC Seal-In",
        compile_only=True,
        locations=locations,
    )
    print(f"Exported native OpenPLC seal-in project to {result.destination}")


if __name__ == "__main__":
    main()
