"""Generate the first native OpenPLC Rockwell-TON lowering fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
    Program,
    Routine,
    SourceExtension,
    SourceNode,
    Tag,
    Task,
)
from twinforge.targets.openplc import OpenPLCNativeProjectExporter


def build_timer_controller() -> Controller:
    """Build a 5-second Rockwell TON and its canonical DN consumer rung."""

    controller = Controller(name="OpenPLCTimer", identity=Identity())
    program = Program(name="PLC_PRG")
    program.add_tag(Tag(name="Enable", data_type="BOOL"))
    program.add_tag(
        Tag(
            name="DelayTimer",
            data_type="TIMER",
            source_extensions=[
                SourceExtension(
                    format="l5x",
                    root=SourceNode(
                        name="Tag",
                        children=[
                            SourceNode(
                                name="Data",
                                attributes={"Format": "Decorated"},
                                children=[
                                    SourceNode(
                                        name="Structure",
                                        children=[
                                            SourceNode(
                                                name="DataValueMember",
                                                attributes={
                                                    "Name": "PRE",
                                                    "Value": "5000",
                                                },
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                )
            ],
        )
    )
    program.add_tag(Tag(name="Output", data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.extend(
        [
            LadderRung(number=0, text="XIC(Enable)TON(DelayTimer,?,?);"),
            LadderRung(number=1, text="XIC(DelayTimer.DN)OTE(Output);"),
        ]
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
    """Write the writable native timer compatibility project."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = OpenPLCNativeProjectExporter().export(
        build_timer_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC TON",
        compile_only=True,
        locations={"Enable": "%QX0.0", "Output": "%QX0.1"},
        timer_elapsed_locations={"DelayTimer": "%MD0"},
    )
    print(f"Exported native OpenPLC timer project to {result.destination}")


if __name__ == "__main__":
    main()
