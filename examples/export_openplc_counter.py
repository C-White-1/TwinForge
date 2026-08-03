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


def build_counter_controller(
    mode: str = "CTU",
    initial_accumulator: int | None = None,
) -> Controller:
    """Build a canonical CTU, CTD, or paired counter source sequence."""

    controller = Controller(name="OpenPLCCounter", identity=Identity())
    program = Program(name="PLC_PRG")
    for name in ("CountPulse", "CountDown", "ResetCounter", "Done"):
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
                                            ),
                                            SourceNode(
                                                name="DataValueMember",
                                                attributes={
                                                    "Name": "ACC",
                                                    "Value": str(
                                                        initial_accumulator
                                                        if initial_accumulator
                                                        is not None
                                                        else (3 if mode != "CTU" else 0)
                                                    ),
                                                },
                                            ),
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
    count_rungs = []
    if mode in {"CTU", "CTUD", "CTUD_SIMULTANEOUS"}:
        count_rungs.append(
            LadderRung(number=0, text="XIC(CountPulse)CTU(PartCounter,?,?);")
        )
    if mode in {"CTD", "CTUD", "CTUD_SIMULTANEOUS"}:
        count_rungs.append(
            LadderRung(
                number=1,
                text=(
                    "XIC(CountPulse)CTD(PartCounter,?,?);"
                    if mode == "CTUD_SIMULTANEOUS"
                    else "XIC(CountDown)CTD(PartCounter,?,?);"
                ),
            )
        )
    routine.ladder_rungs.extend(
        [
            *count_rungs,
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
    """Write a native OpenPLC project using the shared counter state block."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--mode",
        choices=("CTU", "CTD", "CTUD", "CTUD_SIMULTANEOUS"),
        default="CTU",
        help="Canonical Rockwell counter source shape",
    )
    parser.add_argument(
        "--initial-accumulator",
        type=int,
        help="Decorated Rockwell COUNTER.ACC fixture value",
    )
    args = parser.parse_args()
    result = OpenPLCNativeProjectExporter().export(
        build_counter_controller(args.mode, args.initial_accumulator),
        destination=args.destination,
        project_name="TwinForge OpenPLC CTU",
        compile_only=True,
        locations={
            "CountPulse": "%QX0.0",
            "CountDown": "%QX0.1",
            "ResetCounter": "%QX0.2",
            "Done": "%QX0.3",
        },
        counter_accumulator_locations={"PartCounter": "%MD0"},
        counter_status_locations=(
            {"PartCounter": {"OV": "%QX0.4", "UN": "%QX0.5"}}
            if args.mode != "CTU"
            else None
        ),
    )
    print(f"Exported native OpenPLC counter project to {result.destination}")


if __name__ == "__main__":
    main()
