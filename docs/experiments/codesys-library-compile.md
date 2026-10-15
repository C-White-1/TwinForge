# TwinForge_MEBasic in CODESYS: compile and run checks

Purpose: the first compile of TwinForge's generated Structured Text by a real
CODESYS, and a second oracle for the blocks. The test program replays the
same recorded Machine Expert – Basic simulator checks TwinForge's own tests
replay
([counter](machine-expert-basic-counter-simulator.md),
[drum](machine-expert-basic-drum-simulator.md)), so it should report
**29 checks, 0 failures**. Background:
[CODESYS library notes](../references/codesys-library-for-machine-expert-basic-blocks.md).

Menu names below are from general CODESYS 3.5 knowledge and may differ
slightly by version; note what you actually find.

## Generate the files

```
uv run twinforge codesys library --output <folder>
```

This writes `TwinForge_MEBasic.xml` (the counter and drum blocks) and
`TwinForge_MEBasic_Tests.xml` (the same blocks plus the program
`TF_MEBasic_Tests`).

## A. Test project (compile and run)

1. **File → New Project → Standard project**. Pick the *CODESYS Control Win
   V3* device (the SoftPLC), PLC_PRG in Structured Text.
2. Select **Application**, then **Project → Import PLCopenXML…** and choose
   `TwinForge_MEBasic_Tests.xml`. Import all three items into Application.
3. Open **PLC_PRG** and add one line: `TF_MEBasic_Tests();`
4. **Build → Build** (F11). Record every error and warning, with the line it
   points at. This is the most important result.
5. Start the SoftPLC (*CODESYS Control Win SysTray*, then Start PLC), then
   **Online → Login** (download when asked) and **Debug → Start**.
6. Open `TF_MEBasic_Tests` online, or add it to a watch list, and record
   `xDone`, `iChecks`, `iFailures`, `iFirstFailure`. If `iFirstFailure` is
   not 0, its number is listed in the comment at the top of
   `TF_MEBasic_Tests`.

## B. Library project

1. **File → New Project → Libraries → Empty library**.
2. **Project → Project Information**: Company `TwinForge`, Title
   `TwinForge_MEBasic`, Version `0.1.0`.
3. **Project → Import PLCopenXML…**, choose `TwinForge_MEBasic.xml`.
4. Build, then **File → Save Project and Install into Library Repository**
   (or save as a `.library`). Record any messages.

## Results

| Item | Result |
| --- | --- |
| CODESYS version (Help → About) | V3.5 SP22 Patch 3 |
| Import messages (A2, B3) | |
| Build errors / warnings (A4) | Run 2: 0 errors, 0 warnings |
| `xDone` | TRUE |
| `iChecks` (expect 29) | 29 |
| `iFailures` (expect 0) | 0 |
| `iFirstFailure` (expect 0) | 0 |
| Library saved / installed (B4) | Installed; listed in the Library Manager as `TwinForge_MEBasic, 0.1.0 (TwinForge)` |

### Run 1 (2026-10-11)

Build: 501 errors (`C0189 ';' expected instead of ','`, `C0009 Unexpected
token`), all in `TF_MEBasic_Tests` calls. The cause showed in the block's
own declaration: CODESYS underlines the input names `R` and `S` as reserved
(Instruction List operators; ST's `S=`/`R=` set/reset assignments), while
accepting `E`, `D`, `F`, `CU`, `CD`, `PV`. Fixed in TwinForge: the
parameters are now `RESET` and `LOAD` (counter) and `RESET` and `STEP_NO`
(drum; `STEP` is itself an IEC SFC keyword), the exporter maps the source's
pin names onto them, and a test rejects reserved words in generated blocks.
Regenerate the files before run 2.

### Run 2 (2026-10-11)

New standard project (CODESYS Control Win V3), `TwinForge_MEBasic_Tests.xml`
imported into Application, `TF_MEBasic_Tests();` in PLC_PRG. **Build: 0
errors, 0 warnings, "Ready for download"**: the first compile of
TwinForge's generated Structured Text by CODESYS (counter, drum and the
29-check test program).

Run in the CODESYS Control Win V3 SoftPLC: **`xDone` TRUE, `iChecks` 29,
`iFailures` 0, `iFirstFailure` 0.** CODESYS executes the generated counter
and drum exactly as the Machine Expert - Basic simulator behaved, on every
recorded check: a second, independent oracle agreeing with TwinForge's own
replay.

Part B, same day, CODESYS V3.5 SP22 Patch 3: an empty library project with
Company `TwinForge`, Title `TwinForge_MEBasic`, Version `0.1.0` (not
Released; default namespace left empty), `TwinForge_MEBasic.xml` imported,
then saved and installed into the Library Repository. Added to the test
project through the Library Manager, it appears as
**`TwinForge_MEBasic, 0.1.0 (TwinForge)`, namespace `TwinForge_MEBasic`**.

Library run: in the test project the imported copies of `TF_MEBasic_Counter`
and `TF_MEBasic_Drum` were deleted, leaving `TF_MEBasic_Tests` to use the
installed library's blocks; after a reset and start, **29 checks, 0
failures**. The installed library itself reproduces every recorded check.

### Run 3, library 0.2.0 (2026-10-15)

The drum's `P0`..`P7` became one `PATTERN : ARRAY[0..7] OF WORD` input, and
the test program declares each drum check's table as an initialised array
variable. Imported into CODESYS, built and run in the SoftPLC: **29 checks,
0 failures**. CODESYS accepts an array function block input and an
initialised array variable from imported PLCopen XML.

## Notes

Anything surprising, write it here. Screenshots of the build messages and
of the watch values are the most useful.
