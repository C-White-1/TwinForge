"""Recorded vendor behaviour of the generated function blocks, as replayable checks.

Each check is a sequence observed in the Machine Expert - Basic 3.0 simulator
(docs/experiments/machine-expert-basic-counter-simulator.md and
machine-expert-basic-drum-simulator.md), written as block calls and the
values the simulator showed afterwards. One call of a block is one
controller scan of it. TwinForge replays the checks on each block's
Structured Text in its own tests, and writes them into a test program a
target can run (`plcopen_library_package`), so both test the same
observations.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .plcopen_library import MACHINE_EXPERT_BASIC_COUNTER, MACHINE_EXPERT_BASIC_DRUM, GeneratedFunctionBlock

Value = bool | int

# Pins below use the blocks' parameter names: the source's R and S are
# RESET and LOAD (a drum's step output S is STEP_NO), because R and S are
# reserved words in CODESYS. Labels keep the source's names.


@dataclass(frozen=True)
class Scan:
    """One call of the block. A BOOL input not named is FALSE; any other
    input keeps its last value (initially the check's constant)."""

    inputs: Mapping[str, Value] = field(default_factory=dict)


@dataclass(frozen=True)
class Write:
    """Other logic writing the variable bound to an in-out parameter."""

    variable: str
    value: Value


@dataclass(frozen=True)
class Expect:
    """Values the simulator showed after the preceding scans."""

    label: str
    values: Mapping[str, Value]


Step = Scan | Write | Expect


@dataclass(frozen=True)
class Check:
    name: str
    block: GeneratedFunctionBlock
    constants: Mapping[str, Value]
    steps: tuple[Step, ...]


def pulse(*pins: str, **held: Value) -> tuple[Scan, Scan]:
    """Pins on for one scan, then off: an input forced to 1, then 0."""
    return Scan({**held, **dict.fromkeys(pins, True)}), Scan(dict(held))


def counter(label: str, cv: int, d: bool, e: bool, f: bool) -> Expect:
    """The four columns recorded for a counter: V, D, E, F."""
    return Expect(label, {"CV": cv, "D": d, "E": e, "F": f})


def drum(label: str, step: int, full: bool, on: str) -> Expect:
    """The columns recorded for fixture 14's drum: S (the block's STEP_NO), F,
    and which of its outputs %Q0.0-%Q0.3 (bits B0-B3) are on."""
    return Expect(label, {"STEP_NO": step, "F": full, **{f"B{bit}": str(bit) in on for bit in range(4)}})


# Simulator project 13_counter_simulation, preset 3. Where the simulator's
# animation table wrote %Ci.V = 9999 directly, the checks load 9999 through
# S with PV 9999 and restore PV 3; the next scan recomputes D, leaving the
# same state (V 9999, D/E/F off).
_LOAD_9999 = (Scan({"LOAD": True, "PV": 9999}), Scan({"PV": 3}))

COUNTER_CHECKS = (
    Check("Counter_Counts", MACHINE_EXPERT_BASIC_COUNTER, {"PV": 3}, (
        *pulse("CU"), *pulse("CU"), *pulse("CU"), counter("A1 three counts reach the preset", 3, True, False, False),
        *pulse("CU"), counter("A2 D clears off the preset", 4, False, False, False),
        *pulse("CD"), counter("A3 D sets again from above", 3, True, False, False),
    )),
    Check("Counter_Empty", MACHINE_EXPERT_BASIC_COUNTER, {"PV": 3}, (
        *pulse("CU"), *pulse("CD"), counter("B1 reaching 0 does not set E", 0, False, False, False),
        *pulse("CD"), counter("B2 the 0 -> 9999 wrap sets E", 9999, False, True, False),
        *pulse("CD"), counter("B3 the next count down clears E", 9998, False, False, False),
    )),
    Check("Counter_Full", MACHINE_EXPERT_BASIC_COUNTER, {"PV": 3}, (
        *pulse("CD"), counter("B2 again: wrap down", 9999, False, True, False),
        *pulse("CU"), counter("C2 the 9999 -> 0 wrap sets F and clears E", 0, False, False, True),
        *pulse("CU"), counter("C3 the next count up clears F", 1, False, False, False),
    )),
    Check("Counter_SetReset", MACHINE_EXPERT_BASIC_COUNTER, {"PV": 3}, (
        *pulse("RESET"), *pulse("LOAD"), counter("C1 S loads the preset and sets D", 3, True, False, False),
        Scan({"RESET": True, "LOAD": True}), counter("E1 R has priority over S (both held)", 0, False, False, False),
        Scan(), Scan({"LOAD": True, "PV": 9999}), counter("C1'' S loads preset 9999", 9999, True, False, False),
    )),
    Check("Counter_Cancel", MACHINE_EXPERT_BASIC_COUNTER, {"PV": 3}, (
        *pulse("CU", "CD"), counter("D1 CU and CD together from 0", 0, False, False, False),
        *_LOAD_9999, *pulse("CU", "CD"), counter("G2 CU and CD together cancel", 9999, False, False, False),
    )),
    Check("Counter_DownClearsFull", MACHINE_EXPERT_BASIC_COUNTER, {"PV": 3}, (
        *_LOAD_9999, *pulse("CU"), counter("G1 wrap up sets F", 0, False, False, True),
        *pulse("CD"), counter("G1 the next count down clears F", 9999, False, True, False),
    )),
)

# Simulator project 14_drum_simulation: 4 steps; step 1 sets bits 0 and 1
# (%Q0.0, %Q0.1), step 2 bit 2, step 3 bit 3. The constants are the ones the
# parser derives from that fixture (TwinForge's tests check they agree).
DRUM_CONSTANTS: Mapping[str, Value] = {
    "NSTEPS": 4, "P0": 0x0000, "P1": 0x0003, "P2": 0x0004, "P3": 0x0008,
    "P4": 0x0000, "P5": 0x0000, "P6": 0x0000, "P7": 0x0000,
}

DRUM_CHECKS = (
    Check("Drum_Steps", MACHINE_EXPERT_BASIC_DRUM, DRUM_CONSTANTS, (
        *pulse("RESET"), drum("A1 reset", 0, False, ""),
        *pulse("U"), drum("A2 step 1 sets %Q0.0 and %Q0.1", 1, False, "01"),
        *pulse("U"), drum("A3 a step writes 0s too", 2, False, "2"),
        *pulse("U"), drum("A4 F on the last step", 3, True, "3"),
        *pulse("U"), drum("A5 wraps to step 0 and F clears", 0, False, ""),
    )),
    Check("Drum_ResetHeld", MACHINE_EXPERT_BASIC_DRUM, DRUM_CONSTANTS, (
        *pulse("U"), *pulse("U"), drum("B1 step 2", 2, False, "2"),
        Scan({"RESET": True}), Scan({"RESET": True, "U": True}), Scan({"RESET": True}),
        drum("B2 R held wins over U and writes step 0", 0, False, ""),
        Scan(), drum("B3 R released", 0, False, ""),
    )),
    Check("Drum_WritesOnChange", MACHINE_EXPERT_BASIC_DRUM, DRUM_CONSTANTS, (
        *pulse("U"), drum("C1 step 1", 1, False, "01"),
        Write("B1", False), Scan(), Scan(),
        drum("C2 another rung's reset of %Q0.1 stands", 1, False, "0"),
        *pulse("U"), drum("the next step change writes again", 2, False, "2"),
    )),
    Check("Drum_ResetRewrites", MACHINE_EXPERT_BASIC_DRUM, DRUM_CONSTANTS, (
        Scan({"RESET": True}), Write("B0", True), Scan({"RESET": True}),
        drum("E1b R held rewrites step 0 every scan", 0, False, ""),
        Scan(), Write("B0", True), Scan(), drum("with R released, a set stands", 0, False, "0"),
    )),
)

CHECKS: tuple[Check, ...] = (*COUNTER_CHECKS, *DRUM_CHECKS)
