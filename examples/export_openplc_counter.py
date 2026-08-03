"""Generate the evidenced Rockwell-compatible native OpenPLC CTU fixture."""

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


def build_counter_controller() -> Controller:
    """Build the canonical CTU, DN consumer, and reset source sequence."""

    controller = Controller(name="OpenPLCCounter", identity=Identity())
    program = Program(name="PLC_PRG")
    for name in ("CountPulse", "ResetCounter", "Done"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    program.add_tag(
        Tag(
            name="PartCounter",
            data_type="COUNTER",
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
                                                    "Value": "3",
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
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.extend(
        [
            LadderRung(
                number=0,
                text="XIC(CountPulse)CTU(PartCounter,?,?);",
            ),
            LadderRung(number=1, text="XIC(PartCounter.DN)OTE(Done);"),
            LadderRung(number=2, text="XIC(ResetCounter)RES(PartCounter);"),
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
    """Write a native OpenPLC project using the `TF_CTU` compatibility block."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = OpenPLCNativeProjectExporter().export(
        build_counter_controller(),
        destination=args.destination,
        project_name="TwinForge OpenPLC CTU",
        compile_only=True,
        locations={
            "CountPulse": "%QX0.0",
            "ResetCounter": "%QX0.1",
            "Done": "%QX0.2",
        },
        counter_accumulator_locations={"PartCounter": "%MD0"},
    )
    print(f"Exported native OpenPLC counter project to {result.destination}")


if __name__ == "__main__":
    main()
