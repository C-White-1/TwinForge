# Machine Expert – Basic `.smbp` project format: provisional specification

Status: provisional specification, 2026-10-07. Read-only capture, basic
mapping (controller, symbol tags, POU routines) and ladder networks built
from the grid rules below are implemented in `parsers/machine_expert_basic/`. Delivery is
tracked in the [Machine Expert – Basic roadmap](../roadmaps/machine-expert-basic-roadmap.md).
This document records what was directly observed in public sample files so
implementation can be specification-driven. Rules under "Proposed capture
contract" are TwinForge requirements, not a claim to reproduce Schneider's
complete grammar.

## Evidence and limits

63 `.smbp` files (Machine Expert – Basic, formerly SoMachine Basic, for the
Modicon M221) were downloaded on 2026-10-07 from public GitHub repositories
into the ignored `reference/machine-expert/smbp/`. Repository URLs and
licences are recorded in `reference/machine-expert/SOURCES.md`; most of the
source repositories carry no licence, so the files stay local-only under the
[artifact policy](../artifact-policy.md) and must not be copied into
`tests/` or `examples/`. The research scripts below live in `examples/` and
take the sample directory as an argument.

SHA-256 hashes, sizes and every count quoted below are reproduced by:

```powershell
python examples/analyze_smbp_corpus.py reference/machine-expert/smbp reference/machine-expert/smbp_inventory.json
```

The script is tracked; the samples it reads are not. It is a research aid,
not a production capture implementation. No two files have
identical content.

The corpus is weak in specific ways; read every observation in that light:

- 54 of 63 files come from one author (`ss56`) and are short training
  exercises, mostly single-rung or few-rung.
- All 62 readable files target a TM221 CPU (`TM221CE16R` in 48). Only one
  expansion module appears (`TM3AM6/G`, twice). No cartridge-heavy,
  communication-heavy or multi-expansion project is present.
- `ProjectVersion` spans 1.6.0.0 to 2.7.0.0, but versions after 2.2 have
  only one to three files each.
- Inspection checked XML well-formedness only. Nothing was opened in Machine
  Expert – Basic, compiled, or downloaded to a controller.

### User-made fixtures (Machine Expert – Basic 3.0)

To fill specific gaps, 15 small projects were drawn by hand in Machine
Expert – Basic (`ProjectVersion` 3.0.0.0, `ManagementLevel`
`FunctLevelMan21_0`, TM221CE16R) and committed in
`examples/machine_expert_basic/`. Unlike the downloaded samples they are
redistributable, and `tests/test_machine_expert_basic_fixtures.py` exercises
every one. Each was compared with an editor screenshot of the same rung.
Their element paths are those of the 63 older samples plus exactly six,
all from settings no sample happened to use: `TimerTM/IsRetentive` and
`TimerTM/IsDynamicPreset` (`05c_timer`), and `Counters/Counter` with its
`Address`, `Index`, `Preset` and `Symbol` (`06b_counter`, `09_symbols`). A
plain 3.0 rung (`01_series`) adds nothing, so these come from content, not
from the version. The `Counter` cell `ElementType` is likewise new.

| Fixture | Settles |
| --- | --- |
| `01_series` | Baseline series rung; output in column 10 on 3.0 |
| `02_parallel`, `03_nested`, `04_two_outputs` | Vertical links sit on a cell's right edge (seen in the editor, not only inferred from IL); nested branches; output fan-out |
| `05_timer`, `05b_timer`, `05c_timer` | Timer width 2; which timer settings are stored, and when |
| `06_counter`, `06b_counter` | `Counter` element type; fixed pin rows (corrects an earlier rule); two wired outputs; counter preset storage |
| `07_compare_operate` | Comparison and output-side Operation are both 2 columns wide |
| `08_edges` | `RisingEdge`/`FallingEdge` contacts; two rungs in one POU; a leading wire before the first contact |
| `09_symbols` | Where I/O, memory-bit and counter symbols live; named but unused objects |
| `10_il_only` | IL rungs store no cells; the editor pads IL columns itself |
| `11_encrypted` | `CryptedProject` on 3.0 |
| `12_edited` | Grid and IL after an edit (see open questions) |

## Container and encoding

An `.smbp` is a single UTF-8 XML document with a byte-order mark (all 63
files). There is no ZIP container. Elements are .NET `XmlSerializer` output:
the root declares `xsi`/`xsd` namespaces, values are element text rather than
attributes, and attributes are rare (`xsi:nil` on `GlobalProperties/UnitId`,
`Type` on a few function-block parameter elements).

Two root elements were observed:

| Root | Files | Content |
| --- | --- | --- |
| `ProjectDescriptor` | 62 | Readable project |
| `CryptedProject` | 1 | `ProjectVersion`, an opaque `Crypted` text blob (14,464 chars), and `PublicProperties` (project name, company and user information) |

A `CryptedProject` must be captured as such: public properties readable, the
blob preserved verbatim, no attempt to decrypt. `11_encrypted` shows the
same shape on 3.0. Its readable name is the project's internal name
(`01_series`, the project it was copied from), not the file name. The file
is 14 KB against 82 KB for the readable original, so the content is
probably compressed before encryption; this is an observation only.

## `ProjectDescriptor` top level

| Element | Present | Content |
| --- | --- | --- |
| `ProjectVersion` | 62 | Editor file-format version, e.g. `2.2.0.0` |
| `ManagementLevel` | 62 | e.g. `FunctLevelMan11_0`; eight distinct values. Meaning not established |
| `Name`, `FullName` | 62 | Project name and the absolute path it was last saved to on the author's machine |
| `CurrentCultureName` | 34 | e.g. `en-GB` |
| `HardwareConfiguration` | 62 | `Plc/Cpu`, `Plc/Extensions`, `Plc/Cartridge1`, serial-line and power-budget elements |
| `SoftwareConfiguration` | 62 | Logic, memory objects, function-block configuration, tasks, symbols |
| `GlobalProperties` | 62 | Project and application protection, download settings, company/user information |
| `DisplayUserLabelsConfiguration` | 62 | Label languages and translations |
| `ReportConfiguration` | 62 | Print page setup |

Element sets grow with `ProjectVersion` (for example `UserFunctionPous` and
`DownloadSettings/*` appear only in some files). Capture must therefore treat
every child list as open.

`GlobalProperties/ProjectProtection/Password` and
`ApplicationProtection/Password` exist but are empty in every sample. A
populated password field is security-sensitive; capture should preserve it
but reports must not print it.

## Hardware configuration

`HardwareConfiguration/Plc/Cpu` carries the catalogue `Reference`, I/O counts,
electrical consumption, and per-point I/O lists (`DigitalInputs/DiscretInput`,
`DigitalOutputs`, `AnalogInputs`, `AnalogOutputs`, high-speed counters, pulse
train outputs, Ethernet and Modbus mapping). Each I/O point is an
`Address`/`Index` pair, with `Symbol` and `Comment` when the user named it.
Expansion modules appear as children of `Plc/Extensions` with their own
`Reference`.

## Software configuration: memory objects and symbols

Memory objects and function-block instances are declared outside the logic,
as lists under `SoftwareConfiguration`: `MemoryBits/MemoryBit`,
`MemoryWords/MemoryWord`, `MemoryFloats`, `MemoryDoubleWords`, constants,
`SystemBits` (~50 per file), `SystemWords` (~147 per file), `Timers/TimerTM`,
`Counters`, `Drums`, `Registers`, `ShiftBitRegisters`, `StepCounters`,
`MessageBlocks`, `Pids`, `ScheduleBlocks` and others. Each entry is keyed by
`Address` (`%M0`, `%TM0`) with an `Index` and, where named, `Symbol` and
`Comment`.

Function-block parameters live here, not in the rung. Example:

```xml
<TimerTM>
  <Address>%TM0</Address>
  <Index>0</Index>
  <Preset>10</Preset>
  <Base>OneSecond</Base>
</TimerTM>
```

A rung that uses `%TM0` must be joined to this entry to know its preset and
time base.

### Object data types

The file stores no data types; the object's address prefix decides it.
Schneider documents the types in the *EcoStruxure Machine Expert – Basic
Generic Functions Library Guide*, EIO0000003289.04 (© 2025), installed with
the editor as `Help/en-GB/sombgflg.chm`:

| Objects | Documented as | IEC type | Guide page |
| --- | --- | --- | --- |
| `%I`, `%Q` | digital input/output bit objects | BOOL | I/O Objects |
| `%M`, `%S` | memory and system bit objects | BOOL | Memory Bit Objects |
| `%MW`, `%KW`, `%IW`, `%QW`, `%IWS`, `%QWS`, `%SW` | 16-bit words, two's complement, -32768..32767 | INT | Word Objects |
| `%QWE`, `%IWE`, `%QWM`, `%IWM` | listed under "Words" with `%MW` in operand tables | INT | Integer/Floating Conversion; Word, Double Word, and Floating Point Tables Assignment |
| `%MD` | 32-bit two's complement | DINT | Floating Point and Double Word Objects |
| `%MF` | IEEE 754 single precision | REAL | Floating Point and Double Word Objects |
| `%TM`, `%C`, `%DR`, ... | function blocks | none (not an elementary type) | Timer (%TM), Counter (%C) |

The word-object page names one exception, the Fast Counter function block
(0..65535); it is not one of the mapped tables. The samples agree where they
can: `%MF` takes float literals (`%MF2 := 1.0`), bits are used as contacts
and coils. `schema/machine_expert_basic/mapping.py` holds the per-table type.

**Settings at their default value are not written**, and an object whose
settings are all default and that has no symbol has no entry at all.
Established by changing one setting at a time in the fixtures:

| Setting | Stored as | When absent | Fixture |
| --- | --- | --- | --- |
| Timer type | `TimerTM/Type` (`TOF`) | TON | `05_timer` vs `05b_timer` |
| Retentive | `TimerTM/IsRetentive` = `true` | false | `05c_timer` |
| Dynamic preset | `TimerTM/IsDynamicPreset` = `true` | false | `05c_timer` |
| Counter preset | `Counters/Counter/Preset` | 9999; `<Counters />` is empty | `06_counter` vs `06b_counter` |
| Counter symbol | `Counters/Counter/Symbol` | no symbol | `09_symbols` |

A reader must therefore supply defaults itself: a rung that uses `%C0` with
no `Counter` entry means preset 9999, not "unknown". TP is listed in the
editor's timer types but has not been observed in a file. Timer and counter
configuration appears only here, never in the IL (`BLK %TM0 … IN … Q` is
the same for TON and TOF).

## Logic: POUs and rungs

```text
SoftwareConfiguration/Pous/ProgramOrganizationUnits   (one per POU)
├── Name, SectionNumber
└── Rungs/RungEntity                                   (one per rung)
    ├── Name, Label, MainComment
    ├── IsLadderSelected       true | false
    ├── LadderElements/LadderEntity*                   ladder grid cells
    └── InstructionLines/InstructionLineEntity*        IL text + Comment
```

60 files have one POU, 2 have two, and one has none. There are 358 rungs in
total.

**Every rung stores Instruction List (IL).** `InstructionLines` is present in
all 358 rungs. A rung edited in Ladder additionally stores its grid. 91 rungs
have no grid cells at all (IL-only, `IsLadderSelected=false`). Three further
rungs have `IsLadderSelected=false` and a single `None` cell. IL text is
column-aligned with variable whitespace (`LD    %M0`, `LD  %I0.4`), so
tokens must be split on runs of whitespace. The editor adds the padding
itself: in `10_il_only`, `LD %I0.0` typed by hand was saved as
`LD    %I0.0`.

This dual storage is the most useful property of the format: IL is an
editor-generated linear form of the same logic, so it can be used to check
how the grid is interpreted. Whether the editor regenerates IL from the grid
on every save, or the two can disagree, has not been established.

### Ladder cells

Each `LadderEntity` is one grid cell:

| Field | Present in | Content |
| --- | --- | --- |
| `ElementType` | all 3,319 | See table below |
| `Row`, `Column` | all | Zero-based grid position |
| `ChosenConnection` | all | Comma-separated subset of `Up`, `Down`, `Left`, `Right`, or `None` |
| `Descriptor` | 1,673 | Operand: an address (`%I0.1`, `%TM0`), or an instance number for `RisingEdgeBlock` |
| `Symbol`, `Comment` | 664, 970 | Copy of the operand's symbol-table entry |
| `ComparisonExpression` | 80 | Text of a `Comparison` box |
| `OperationExpression` | 56 | Text of an `Operation` box |

`Symbol` and `Comment` are denormalised copies: in all 234 cells whose
operand has a symbol-table entry (in `HardwareConfiguration` or
`SoftwareConfiguration`), both fields equal the table's values. The table is
the source of truth; capture must still preserve the cell copies.

Empty grid positions are **not stored**. A rung's grid is the set of stored
cells; any missing position is empty.

Grid width is not fixed. The output element sits in column 10 in every file
except one (`asu-in-ua/pou_laba3.smbp`, `ProjectVersion` 2.5.0.0), where it
sits in column 11. The only 2.7.0.0 file uses column 10, so the width is not
simply a version property. Capture must not hard-code a column count. Rows
observed: 0–9.

### Element types

| `ElementType` | Count | Observed `ChosenConnection` | IL counterpart (observed) |
| --- | --- | --- | --- |
| `Line` | 2,282 | mostly `Left, Right` | none (wire) |
| `NormalContact` | 290 | `Left, Right`; branch ends add `Up`/`Down` | `LD` / `AND` / `OR` |
| `NegatedContact` | 114 | as above | `LDN` / `ANDN` / `ORN` |
| `RisingEdge`, `FallingEdge` | 17, 16 | `Left, Right` | `LDR` / `LDF` |
| `VerticalLine` | 118 | `Up, Right`, `Up, Down, Right`, `Up, Down`, `Down, Right` | none (branch wiring) |
| `Coil` | 157 | `Left` | `ST` |
| `NegativeCoil` | 7 | `Left` | `STN` |
| `SetCoil`, `ResetCoil` | 53, 67 | `Left` | `S`, `R` |
| `Comparison` | 80 | `Left, Right` | `LD [ %QW0.100 > 1000 ]`; an assignment inside one was seen as `OPER [ %TM0.P := %MW0 ]` |
| `Operation` | 56 | `Left` (output side) or `Left, Right` | `[ %MW101 := %MW101 + 1 ]` |
| `Timer` | 32 | `Left, Right` or `Left` | `BLK %TMn` … `IN` … `OUT_BLK` … `END_BLK` |
| `Counter` | 0 (1 in `06_counter`) | `Left, Right` | `BLK %Cn` … `R` / `CU` … `OUT_BLK` … `LD D` / `LD F` … `END_BLK` |
| `Drum` | 8 | `Left, Right` | `BLK %DRn` … `R` / `U` … `END_BLK` |
| `WriteVarBasic` | 1 | `Left, Right` | `BLK %WRITE_VARn` … `Execute` … `END_BLK` |
| `RisingEdgeBlock` | 4 | `Left, Right` | `RISINGn`, where `n` is the cell's `Descriptor` |
| `Not` | 1 | `Left, Right` | `N` |
| `Xor` | 2 | `Left, Right` | `XOR` |
| `Short` | 9 | `Left, Right` | `LD 1` when it starts the rung |
| `None` | 5 | `None` | none: an empty cell the editor touched (see below) |

Notes:

- `Comparison` is a generic expression box in a contact position, not only a
  comparison. 30 `Comparison` cells hold assignments (`%TM0.P := %MW0`,
  `%MF1 := %MF2 * %MF3`). Do not infer behaviour from the element type
  name; parse the expression.
- **Blocks use more than one row.** In `ss56/drum-test.smbp` the drum `%DR0`
  sits at row 0, column 1, with a `RisingEdge` at row 0, column 0 wired to
  its first input, and a `FallingEdge` at row 1, column 0 wired to its second
  input. The IL makes the pin assignment explicit
  (`LDR %I0.0 | R | LDF %I0.0 | U`). Pin names (`IN`, `R`, `U`, `Execute`)
  and output names (`Q`, `F`, `Done`) appear only in the IL.
- Element widths are not stored. The grid-against-IL check below confirms
  `Timer`, `Counter`, `Drum` and `Comparison` are 2 columns wide and
  `WriteVarBasic` is 4 (one sample only); all other elements are 1. An
  `Operation` in the output position is also 2 wide: it starts one column
  before a coil would (`07_compare_operate`: column 9 of 10). The
  2-column timer, counter, comparison and operation are visible in the
  editor screenshots of the fixtures.
- `None` cells are leftovers of editor selection, not logic. In `03_nested`
  the one `None` cell is exactly where an empty cell was selected in the
  editor, and it disappears in `12_edited` after the rung was rebuilt.

### Grid semantics, verified against IL

The rules below were checked against the IL of **every one of the 264 rungs
that have grid cells** in the downloaded samples, and of the user-made
fixtures in `examples/machine_expert_basic/`, with no exceptions:

```powershell
python examples/check_smbp_grid_vs_il.py reference/machine-expert/smbp
python examples/check_smbp_grid_vs_il.py examples/machine_expert_basic
```

The script evaluates each grid as a power-flow network and runs a small IL
interpreter on the same rung. It then compares each coil, operation and
function-block input pin over every combination of the rung's inputs (no
rung needed sampling). As a negative control,
`--vertical-on-left` moves vertical links to the cell's left edge; 51 rungs
then mismatch, so the check does discriminate.

1. Number the vertical edges of row `r` as nodes `(r, 0)` … `(r, W)`. Node
   `(r, 0)` is the left power rail, for every row.
2. A cell at `(r, c)` with width `w` connects node `(r, c)` to node
   `(r, c + w)`. It reads its left node only if `ChosenConnection` contains
   `Left`.
3. `Down` on a cell joins its **right** node `(r, c + w)` to `(r + 1, c + w)`;
   `Up` joins it to `(r - 1, c + w)`. Joined nodes form a wired OR. A
   `VerticalLine` cell has no horizontal conduction: it only carries this
   vertical link and, with `Right`, feeds the next cell in its row.
4. Every function-block pin sits on a **fixed row offset for its block
   type**, and that table is not stored in the file:

   | Block | Inputs (row offset) | Outputs (row offset) | Evidence |
   | --- | --- | --- | --- |
   | `Timer` | `IN` 0 | `Q` 0 | samples, `05_timer` |
   | `Counter` | `R` 0, `S` 1, `CU` 2, `CD` 3 | `E` 0, `D` 1, `F` 2 | `06_counter` (all pins drawn) |
   | `Drum` | `R` 0, `U` 1 | `F` 0 | `ss56/drum-test` |
   | `WriteVarBasic` | `Execute` 0 | `Done` 0 | `ss56/WriteVar` (one sample) |

   Input pin `p` of a block at `(r, c)` reads node `(r + row(p), c)`. The IL
   lists only the **wired** pins, so a pin's position in the IL does not give
   its row: in `06_counter`, `CU` is the second IL pin but sits on row 2,
   because `S` on row 1 is unwired. (An earlier version of this note stated
   the IL-order rule; it held in the downloaded samples only because their
   wired pins happened to start at row 0 with no gaps. Substituting it back
   makes `06_counter` fail.)
5. Output pin `p` drives node `(r + row(p), c + w)` when the cell that
   starts there has `Left`. In `06_counter`, `D` drives row 1 and `F` row 2.
   The block's own `Right` is **not** reliable: two `Timer` cells lack
   `Right` although their output is wired and the IL reads `Q`. These are
   the only cases where a cell's `Right` and its neighbour's `Left` disagree.
6. `None` cells are ignored.

Coverage of the 264 rungs: 55 have vertical links, 41 contain a function
block, 8 use a block with more than one input pin, 3 place a block below row
0, and 3 use the `MULTIFB` IL form. None of the downloaded samples wires
more than one block output in a grid; `06_counter` (two wired outputs, on
rows 1 and 2) is the only evidence for rule 5 beyond row 0. Pin rows for
block types not in the table are unknown, and the checker reports such a
pin as unsupported rather than guessing.

`MULTIFB` (3 rungs, all in the `ProjectVersion` 2.7.0.0 sample) brackets IL
that stores a shared branch point in a temporary bit (`ST %MW2009:X0`) and
reads it back (`LD %MW2009:X0`). Such a write is not a rung output.

What the check does **not** show: that the IL matches what the controller
executes, timer/counter/drum behaviour, or edge semantics. Edges and blocks
are treated as uninterpreted, identical on both sides; only the wiring is
verified.

### Instruction List vocabulary observed

First tokens seen, by frequency: `LD`, `ST`, `AND`, `R`, `ANDN`, `BLK`,
`END_BLK`, `S`, `[`, `OUT_BLK`, `IN`, `OPER`, `LDN`, `)`, `OR`, `LDR`,
`MPS`, `MPP`, `OR(`, `LDF`, `U`, `AND(N`, `AND(`, `STN`, `MULTIFB`, `MRD`,
`CU`, `CD`, `ANDF`, `XOR`, `RISING0`–`RISING3`, `N`, `ORN`, `Execute`.

- `MPS` / `MRD` / `MPP` (push, read, pop) express branches that fan out to
  several outputs.
- `AND(` … `)` and `OR(` … `)` express nested series/parallel groups.
- `BLK` … `OUT_BLK` … `END_BLK` brackets a function-block call: input
  logic before `OUT_BLK`, output logic after.
- `MULTIFB` brackets a multi-branch rung that uses a temporary bit; see
  above.

## Proposed capture contract

These follow the project rules (never discard data, preserve unknown
content, stay vendor-neutral):

1. Capture is lossless. Keep the original bytes and every element, including
   unknown elements and those not yet interpreted (report, label and
   protection settings).
2. Detect the root. `ProjectDescriptor` is captured in full;
   `CryptedProject` is captured as public properties plus the opaque blob,
   flagged as encrypted.
3. Each rung is captured with both its cell list and its IL lines, in source
   order. Neither is derived from the other at capture time.
4. Cells are captured as stored. The capture layer does not fill empty
   positions, normalise `ChosenConnection`, or assume a grid width.
5. Symbol tables are captured from both `HardwareConfiguration` and
   `SoftwareConfiguration`, keyed by address. Cell `Symbol`/`Comment` copies
   are kept and any disagreement with the table is reported, not repaired.
6. Function-block parameters (`TimerTM` preset/base, counters, drums) are
   captured from `SoftwareConfiguration` and joined to rungs by address in the
   parser, not in capture.
7. Password fields are preserved but must never appear in reports.

## Open questions

- Whether IL and grid can disagree in a saved file. None did in 264
  downloaded rungs or 14 fixture rungs. `12_edited` moved a contact in
  `03_nested` (the grid changed, the logic did not) and the IL stayed
  identical and consistent; because the logic was unchanged it cannot show
  whether the editor regenerates IL on save. A logic-changing edit would.
- Widths and pin rows for block types not yet evidenced (only Timer,
  Counter, Drum and WriteVarBasic are known).
- How a TP timer and other non-default values not yet tried are stored;
  the defaults table above covers only what the fixtures exercised.
- What sets grid width (column 10 vs 11). Version 3.0 uses column 10, so
  the one column-11 file (2.5.0.0) is the outlier.
- `ManagementLevel` meaning.
- Content of multi-POU programs, subroutines (`SR`), Grafcet steps,
  user-defined function blocks and user functions: present as elements
  but empty or rare in this corpus. A real-world-sized project is needed.
