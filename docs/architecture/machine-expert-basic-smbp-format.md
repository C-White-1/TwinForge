# Machine Expert – Basic `.smbp` project format: provisional specification

Status: provisional specification, 2026-10-07. Read-only capture and basic
mapping (controller, symbol tags, POU routines with rung IL) are implemented
in `parsers/machine_expert_basic/`; ladder networks are not. Delivery is
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
blob preserved verbatim, no attempt to decrypt.

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
tokens must be split on runs of whitespace.

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
| `Drum` | 8 | `Left, Right` | `BLK %DRn` … `R` / `U` … `END_BLK` |
| `WriteVarBasic` | 1 | `Left, Right` | `BLK %WRITE_VARn` … `Execute` … `END_BLK` |
| `RisingEdgeBlock` | 4 | `Left, Right` | `RISINGn`, where `n` is the cell's `Descriptor` |
| `Not` | 1 | `Left, Right` | `N` |
| `Xor` | 2 | `Left, Right` | `XOR` |
| `Short` | 9 | `Left, Right` | `LD 1` when it starts the rung |
| `None` | 5 | `None` | none: a placeholder |

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
  `Timer`, `Drum` and `Comparison` are 2 columns wide and `WriteVarBasic` is
  4 (one sample only); all other elements are 1.

### Grid semantics, verified against IL

The rules below were checked against the IL of **every one of the 264 rungs
that have grid cells**, with no exceptions:

```powershell
python examples/check_smbp_grid_vs_il.py reference/machine-expert/smbp
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
4. A function block at `(r, c)` takes its *i*-th input pin, in the order the
   pins appear in the IL, from node `(r + i, c)`. Example: the drum's
   `R` pin comes from row `r`, its `U` pin from row `r + 1`.
5. A block's first output drives node `(r, c + w)` when the cell that starts
   there has `Left`. The block's own `Right` is **not** reliable: two `Timer`
   cells lack `Right` although their output is wired and the IL reads `Q`.
   These are the only cases where a cell's `Right` and its neighbour's
   `Left` disagree.
6. `None` cells are ignored.

Coverage of the 264 rungs: 55 have vertical links, 41 contain a function
block, 8 use a block with more than one input pin, 3 place a block below row
0, and 3 use the `MULTIFB` IL form. Multi-output blocks never appear in a
rung that has a grid (`ss56/test4.smbp` uses counter outputs `E`/`D`/`F`, but
only in IL), so rule 5 is unverified for a second output.

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

- Whether IL and grid can disagree in a saved file. None did in 264 rungs.
- Block widths and the second output of a multi-output block; widths for
  element types not in this corpus.
- What sets grid width (column 10 vs 11).
- `ManagementLevel` meaning.
- Content of multi-POU programs, subroutines (`SR`), Grafcet steps,
  user-defined function blocks and user functions: present as elements
  but empty or rare in this corpus. A real-world-sized project is needed.
