# TwinForge_MEBasic: Machine Expert – Basic blocks for CODESYS

IEC 61131-3 function blocks that reproduce the behaviour of two Schneider
Electric EcoStruxure Machine Expert – Basic objects, for programs moved from
an M221 to a CODESYS controller:

| Block | Reproduces | In short |
| --- | --- | --- |
| `TF_MEBasic_Counter` | `%C` counter | Up/down counter, 0..9999 with wrap flags |
| `TF_MEBasic_Drum` | `%DR` drum | Step sequencer, up to 8 steps × 16 control bits |

Neither has an IEC equivalent: IEC `CTUD` does not wrap or set flags the
way `%C` does, and IEC 61131-3 has no drum sequencer at all. Schneider's
own compatible blocks (the TwidoEmulationSupport library) run only inside
Schneider's Machine Expert.

**Status:** version 0.2.1, built and tested with CODESYS V3.5 SP22 Patch 3.
**Licence:** MIT, as part of [TwinForge](../../README.md).
**Not affiliated with or endorsed by Schneider Electric.**

> **Provided as-is, without warranty.** These blocks control machines.
> Test them on your own equipment before relying on them.

## How it was verified

Each block was checked against the Machine Expert – Basic 3.0 simulator,
step by step, and the observations were recorded:
[counter checks](../experiments/machine-expert-basic-counter-simulator.md),
[drum checks](../experiments/machine-expert-basic-drum-simulator.md).
Where Schneider's documentation was wrong or silent, the simulator decided.
For example, `E` is set only on the 0 → 9999 wrap, not on reaching 0.

The 29 recorded checks are one data set
(`src/twinforge/exporters/plcopen_library_checks.py`). They run in three
places:

- **TwinForge's tests**, on each block's Structured Text.
- **A test program, `TF_MEBasic_Tests`**, generated from the same checks.
  It passes 29 of 29 in the CODESYS SoftPLC, both with the blocks imported
  and with the installed library
  ([CODESYS runs](../experiments/codesys-library-compile.md)).
- **Deliberately broken blocks**, as a negative check: TwinForge's tests
  confirm that a broken block fails the checks.

**Not modelled:**

- The system bits `%S17`/`%S18`.
- What a controller restart does to outputs.
- Logic writing a counter's preset or a drum's step while running. A
  counter's `PV` can be changed, but when Basic applies a new preset was
  not checked.

## Getting the library

There is no prebuilt library file yet. Build it from TwinForge (about five
minutes):

1. **Generate the files.** In the TwinForge folder, run
   `uv run twinforge codesys library --output build/codesys-library`. This
   writes `TwinForge_MEBasic.xml` (the blocks) and
   `TwinForge_MEBasic_Tests.xml` (the blocks plus `TF_MEBasic_Tests`).
2. **Create the library project.** In CODESYS: File → New Project →
   Libraries → Empty library.
3. **Fill in Project Information.**
   - Company `TwinForge`, Title `TwinForge_MEBasic`, Version `0.2.1`.
   - On the Properties tab, add `DocFormat` (text) = `reStructuredText`.
4. **Import the blocks.** In the POUs view (View → POUs): Project → Import
   PLCopenXML…, then `TwinForge_MEBasic.xml`.
5. **Save and install.** File → Save Project and Install into Library
   Repository. Keep the readable `.library` rather than a compiled one, so
   users can read the code.
6. **Use it in a project.** Library Manager → Add Library →
   `TwinForge_MEBasic`.

**To run the checks yourself:**

1. Import `TwinForge_MEBasic_Tests.xml` into a standard project.
2. Call `TF_MEBasic_Tests();` from `PLC_PRG`.
3. Run it in the SoftPLC and watch `xDone`, `iChecks` (29), `iFailures`
   (0) and `iFirstFailure`.

If `iFirstFailure` is not 0, its number is listed in the comment at the top
of `TF_MEBasic_Tests`.

The block and parameter descriptions appear as declaration comments and in
the Library Manager. The library's Overview page stays blank: CODESYS
generates that page only with its licensed Library Documentation Support
add-on. This file is the overview instead.

## TF_MEBasic_Counter

Counts 0..9999 and wraps:

- **Wrap down:** counting down from 0 gives 9999 and sets `E`.
- **Wrap up:** counting up from 9999 gives 0 and sets `F`.
- **Flags clear:** the next count in either direction clears either flag.
- **Done:** `D` is TRUE while `CV = PV`.
- **Cancel:** rising edges on `CU` and `CD` in the same call cancel.

| Pin | Type | | Meaning |
| --- | --- | --- | --- |
| `RESET` | BOOL | in | Reset (Basic's `R`): `CV := 0`, `E`, `D`, `F` cleared. Has priority. |
| `LOAD` | BOOL | in | Load (Basic's `S`): `CV := PV`, `D := TRUE`. |
| `CU` | BOOL | in | Count up on a rising edge. |
| `CD` | BOOL | in | Count down on a rising edge. |
| `PV` | INT | in | Preset, 0..9999 (Basic's default: 9999). |
| `E` | BOOL | out | Empty: set by the 0 → 9999 wrap. |
| `D` | BOOL | out | Done: `CV = PV`. |
| `F` | BOOL | out | Full: set by the 9999 → 0 wrap. |
| `CV` | INT | out | Current value. |

Basic's `R` and `S` are reserved words in CODESYS (Instruction List
operators), hence `RESET` and `LOAD`, the names CODESYS's own `CTUD` uses.

```
VAR
    Parts : TF_MEBasic_Counter;
END_VAR

Parts(RESET := xReset, LOAD := FALSE, CU := xSensor, CD := FALSE, PV := 3);
xBatchDone := Parts.D;
```

## TF_MEBasic_Drum

A drum steps through up to 8 steps. Each step's pattern switches up to 16
control bits, `B0`..`B15`.

- **Advance:** a rising edge on `U` advances one step. From the last step it
  wraps to step 0.
- **Last step:** `F` is TRUE on the last step.
- **When bits are written:** only when the step changes, and every call
  while `RESET` is TRUE. In between, other logic can write the same outputs
  and its writes stand. This is how the M221 behaves, and why the bits are
  `VAR_IN_OUT` rather than outputs.

| Pin | Type | | Meaning |
| --- | --- | --- | --- |
| `RESET` | BOOL | in | Reset (Basic's `R`): holds step 0 while TRUE, writing step 0's pattern every call. Has priority. |
| `U` | BOOL | in | Advance one step on a rising edge. |
| `NSTEPS` | INT | in | Number of steps, 1..8. |
| `PATTERN` | ARRAY[0..7] OF WORD | in | `PATTERN[k]` is step k's pattern: bit n switches `Bn`. |
| `F` | BOOL | out | TRUE on the last step (`NSTEPS - 1`). |
| `STEP_NO` | INT | out | Current step (Basic's `%DRi.S`). |
| `B0`..`B15` | BOOL | in/out | The control bits. All 16 must be bound; bind unused ones to one spare BOOL. |

### The pattern

The Drum Assistant's grid becomes one `WORD` per step. Bit n is on when
control bit n is ticked in that step. Written as binary literals, a table
reads like the Assistant's grid turned on its side, with bit 0 on the right:

```
VAR_GLOBAL CONSTANT
    DR0_NSTEPS : INT := 4;
    DR0_PATTERN : ARRAY[0..7] OF WORD := [
        2#0000_0000_0000_0000,  // step 0: all off
        2#0000_0000_0000_0011,  // step 1: B0, B1
        2#0000_0000_0000_0100,  // step 2: B2
        2#0000_0000_0000_1000,  // step 3: B3
        0, 0, 0, 0              // steps 4-7 unused
    ];
END_VAR
```

**Pattern editor.** You can edit the table in a grid, like the Drum
Assistant, with
[`drum_pattern_editor.py`](../../examples/CODESYS/scripts/drum_pattern_editor.py).
With a project open, choose Tools → Scripting → Execute Script File… and
pick it.

- **What it writes:** a marked block per drum in a global variable list
  (default `TF_DrumPatterns`): the step count, the pattern, and your
  output names as comments.
- **Editing:** run it again for the same drum to load and edit that block.
- **How to wire it:** the Messages window shows the call to use.

```
VAR
    Seq : TF_MEBasic_Drum;
    xLamp0, xLamp1, xLamp2, xLamp3, xSpare : BOOL;
END_VAR

Seq(RESET := xReset, U := xNext, NSTEPS := DR0_NSTEPS, PATTERN := DR0_PATTERN,
    B0 := xLamp0, B1 := xLamp1, B2 := xLamp2, B3 := xLamp3,
    B4 := xSpare, B5 := xSpare, B6 := xSpare, B7 := xSpare,
    B8 := xSpare, B9 := xSpare, B10 := xSpare, B11 := xSpare,
    B12 := xSpare, B13 := xSpare, B14 := xSpare, B15 := xSpare);
xLastStep := Seq.F;
```

In ladder or FBD, insert a box of type `TF_MEBasic_Drum` and wire the same
pins.

## Converting whole programs

TwinForge also converts Machine Expert – Basic projects (`.smbp`) to
PLCopen XML. It uses these blocks for every `%C` and `%DR`, and fills in
presets and drum patterns from the project's configuration. See the
[Machine Expert – Basic roadmap](../roadmaps/machine-expert-basic-roadmap.md).

## Versions

| Version | Change |
| --- | --- |
| 0.1.0 | Counter and drum; drum pattern as 8 inputs `P0`..`P7`. |
| 0.2.0 | The drum takes one `PATTERN : ARRAY[0..7] OF WORD`. |
| 0.2.1 | Descriptions for every block and parameter. |
