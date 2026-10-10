# Machine Expert – Basic `.smbp` capture roadmap

This turns the [`.smbp` format specification](../architecture/machine-expert-basic-smbp-format.md)
into a TwinForge capability. Technical observations and the verified grid
rules live in that document; this one tracks delivery.

## Architecture

```text
schema/machine_expert_basic/   observed element grammar + declarative mapping paths
parsers/machine_expert_basic/
  capture.py                   bounded XML capture -> CapturedSection tree
  evidence.py                  SourceExtension snapshots
  project.py                   CapturedSection -> Controller/Program/Routine/Tag
  ladder.py                    grid cells -> LadderRung.network
schema/machine_expert_basic/ladder.py   element mappings, widths, block pin rows
```

An independent package, following the per-format convention of
`parsers/control_expert/` and `parsers/scadapack/` (each format owns its
capture layer). Element names and paths come from
`schema/machine_expert_basic/`, not from the parser code.

Tests use small synthetic `.smbp` documents written in the test files, plus
15 user-made Machine Expert – Basic 3.0 fixtures in
`examples/machine_expert_basic/`. The downloaded samples in
`reference/machine-expert/` are mostly unlicensed and stay local; they are
used only for manual verification.

## Milestone 1: capture and basic mapping

- [x] `capture.py`: UTF-8 (with BOM) XML capture under size, depth and node
  limits, DTDs refused, original bytes kept. Roots: `ProjectDescriptor` →
  `project`, `CryptedProject` → `encrypted_project`, anything else retained
  as unclassified XML. Every element is kept; unknown elements and
  attributes are counted in an `unclassified_content` diagnostic.
- [x] `project.py`: `parse_project()` maps
  - project `Name` → `Controller.name`; CPU `Reference` → controller
    `Identity.product_name`;
  - each named symbol-table entry (hardware I/O and software memory objects)
    → a controller `Tag` with `description` from `Comment` and the address
    in `metadata["source_memory_address"]`, the same key Control Expert uses
    (counter symbols added once `09_symbols` evidenced their location);
  - each POU → a `Program` holding one `Routine` (`LD` if any rung has grid
    cells, else `IL`);
  - each rung → a `LadderRung` with `number` and `comment` (`MainComment`);
    the whole `RungEntity`, grid cells and IL included, is retained as a
    source extension. (Milestone 1 also put the IL in `LadderRung.text`;
    Milestone 2 removed that, see below.)
  - `CryptedProject` → a controller named from `PublicProperties`, with an
    `encrypted_project` diagnostic and no logic.
- Not in this milestone: `LadderRung.network`, function-block parameters,
  tasks, expansion modules, CLI.

Password fields are retained in the captured tree (the capture is lossless)
but are never mapped into the model.

## Milestone 2: ladder networks from the grid

- [x] `ladder.py` builds `LadderRung.network` (`LadderSeries`/`LadderParallel`
  of `LadderInstruction`) from the grid, using the rules verified against IL
  in the format specification, all held in `schema/machine_expert_basic/ladder.py`.
  Joined grid nodes become vertices, cells become edges, outputs lead to one
  virtual sink, and series/parallel reduction yields the same shape L5X and
  CCW rungs use: shared conditions, then a `LadderParallel` of output
  branches, ordered top to bottom as drawn.
- [x] Elements without a portable `LadderOperation` (originally edges,
  comparisons, operations, NOT, XOR, negative coils) stay in the network as `UNSUPPORTED`
  with their element type as `source_mnemonic`, and the rung gets a
  `ladder_unsupported_element` diagnostic. (This is "option 2"; the earlier
  plan of no network for such rungs would have left 172 of 264 sample rungs
  without one.)
- [x] Function blocks follow the Control Expert convention: a block output
  used as a condition is a `BLOCK_OUTPUT_REFERENCE` leaf (`%TM0.Q`); each
  wired input pin is an `UNSUPPORTED` sink annotated `input_pin=<pin>`.
- [x] An instruction's `operand` is the declared symbol when the address has
  one (the model's contract: a tag/variable name), with the address kept as
  an `address=` annotation. `tag_dependencies` therefore resolves `.smbp`
  reads and writes; unnamed addresses stay as the operand and are reported
  as unresolved, not dropped.
- [x] `LadderRung.text` is no longer set. Across TwinForge it means Logix RLL
  text: `rll.py` and `software_calls.py` scan it as RLL (IL `AND(` would read
  as a call), and `tag_dependencies` skips `network` whenever `text` is set.
  The IL stays verbatim in the rung's source extension.
- [x] No network is built, with a diagnostic, for an unknown element type
  (`ladder_unknown_element`), no reachable output (`ladder_no_output`) or
  wiring that does not reduce (`ladder_not_series_parallel`). Elements that
  reach no output are left out and reported (`ladder_disconnected_element`).
- [x] Acceptance: every network is equivalent to its rung's IL, by truth
  table over all inputs. Tested for all 14 fixture grid rungs
  (`tests/test_machine_expert_basic_fixtures.py`) and checked manually for
  all 264 downloaded sample grid rungs; none was unresolved or disconnected.
  Builders with a wrong rule substituted (counter pins in IL order, a
  1-column timer, vertical links on the left edge) fail 2, 3 and 5 fixture
  rungs, so the check discriminates.

## Portable operations for `UNSUPPORTED` elements

The remaining `UNSUPPORTED` elements fall into four groups:

- [x] **A. IEC 61131-3 standard elements.** Added to the neutral model:
  `POSITIVE_TRANSITION_CONTACT`, `NEGATIVE_TRANSITION_CONTACT` (-|P|-,
  -|N|-) and `NEGATED_COIL` (-(/)-). `RisingEdge`, `FallingEdge` and
  `NegativeCoil` map to them; so does Control Expert's `PContact`.
  `tag_dependencies` reads transition contacts' operands and treats a
  negated coil as a write; the SVG exporter draws P, N and / marks. The
  CODESYS/CCW target has no evidenced mapping for them yet and keeps its
  existing handling of operations it does not list. Sample rungs still
  containing `UNSUPPORTED`: 170 → 152 of 264.
- [ ] **B. Schneider power-flow operators** (`Not`, `Xor`,
  `RisingEdgeBlock`; 7 occurrences). No IEC ladder equivalent.
- [x] **C. Expressions** (2026-10-10). Model: `Expression` (literal,
  variable, or binary node with an IEC operator; every node typed INT,
  DINT, REAL or BOOL), `LadderOperation.COMPARISON` (a condition) and
  `ASSIGNMENT` (an output that passes power on), and an optional
  `LadderInstruction.expression`. `parsers/machine_expert_basic/expression.py`
  parses the box grammar (operands, integer/real literals including
  negative ones, `+ - * /`, brackets, `= <> < > <= >=`, `:=`), types
  operands by address prefix from the guide (`expression_operand_types`),
  lets an integer literal adopt its context (`3` becomes `3.0` beside a
  REAL), and refuses mixed types, member/bit reads (`%TM0.P`), functions
  other than the shift instructions (`SHL`, `SHR`, `ROL`, `ROR`, a `call`
  node; added 2026-10-10) and out-of-range literals, keeping such boxes
  `UNSUPPORTED` with a `reason=`. The original text stays as a `source_expression=` annotation.
  The PLCopen exporter emits each tree as single IEC functions (`ADD`,
  `SUB`, `MUL`, `DIV`, `MOVE`, `EQ`...`GE`) chained by EN/ENO: nested
  arithmetic writes typed temporaries, an assignment's top level writes
  its target, and a comparison writes a BOOL temporary read by a contact
  wired from the comparison's ENO. Unnamed operands get typed surrogates.
  Recorded, not modelled (Generic Functions Library Guide EIO0000003289.04,
  Arithmetic Operators on Integers): on overflow or division by zero the
  controller sets %S18 and the result is "not significant"; CODESYS
  integer division by zero raises an exception instead. Samples: 300 of
  311 expressions convert (the rest are functions or timer-preset
  writes); all 358 networks remain equivalent to their IL; 332 of 358
  rungs export as LD. Tests execute the emitted functions and compare
  final values with the expression trees over random inputs; reversing
  operands or writing a temporary instead of the target is caught.
- [x] **D. Function-block pins**, timers (2026-10-10). New model operation
  `FUNCTION_BLOCK_INPUT` (operand `instance.pin`, the mirror of
  `BLOCK_OUTPUT_REFERENCE`) replaces the `UNSUPPORTED` + `input_pin=` sink
  for every block. Timers referenced in logic or configured get a tag
  (named by symbol, or by address when unnamed) typed `TON`/`TOF`/`TP` with
  `metadata["iec_function_block_inputs"] = {"PT": "TIME#<ms>ms"}`; PT is
  Preset x Time Base with the documented defaults (TON, 9999, 1 min;
  `TimerSpec`). Time-base spellings come from the editor's
  `TimerTimeBaseEnum` (OneMinute, OneSecond, OneHundredMilliSeconds,
  TenMilliSeconds); the 1 ms spelling was not found and is not converted.
  Not converted, with `timer_not_converted`: Retentive, Dynamic Preset, or a
  program write to `%TMi.P` (by default a written preset applies only on
  the next activation, unlike IEC). A timer's Q read as a contact
  (`%TM2.Q`) becomes the instance member. The PLCopen exporter emits a TC6
  `block` per instance per rung: IN wired from the pin's condition, PT
  from an `inVariable`, Q feeding its readers; CODESYS declares
  `Standard.TON` and references the Standard library. Samples: 50 of 54
  timers convert (the 4 others write their preset); 46 blocks emitted; all
  62 readable sample exports validate against TC6.
- [x] **D. Function-block pins**, counters (2026-10-10). Every counter the logic uses or the file configures
  gets a tag (by symbol, or by address when unnamed) with
  `data_type="Counter"`, `metadata["function_block_semantics"] =
  "machine-expert-basic.counter"` and its preset as `PV` (default 9999;
  `CounterSpec`). The PLCopen exporter maps that identifier to the
  TwinForge-generated `TF_MEBasic_Counter` function block
  (`exporters/plcopen_library.py`), writes its definition once (before the
  programs in the standard profile; as a CODESYS `pou` object listed in the
  project tree), and emits each instance as a TC6 block with `PV` as a
  constant input. Block handling is now per-type (`BlockInterface`) rather
  than timer-specific. The body was settled against the Machine Expert –
  Basic 3.0 simulator
  ([checklist and results](../experiments/machine-expert-basic-counter-simulator.md)),
  which corrected the guide on two points (`E` sets only on the wrap, not on
  reaching 0; counting up clears `E`) and settled `CU`+`CD` in one scan
  (they cancel). Tests execute the generated ST against the recorded
  sequences, and the block is marked verified; generated blocks that are not
  stay opt-in (`include_unverified_blocks`). Fixture
  `13_counter_simulation.smbp` is the simulator project. 334 of 358 sample
  rungs export as LD. Not covered: logic writing `%Ci.P`.
- [ ] **D. Function-block pins**, drums and `%WRITE_VAR`: kept as
  `FUNCTION_BLOCK_INPUT` in the network but not exported.

## Instruction List rungs

Decided 2026-10-09: convert IL to a ladder network where it is
ladder-expressible (B), keep the IL text as the fallback (A). IEC 61131-3
deprecated IL in its 2013 edition, which argues against making it a
first-class model concept.

- [x] B: `instruction_list.py` replays a rung's IL with a ladder condition
  as the accumulator (`LD`/`AND`/`OR` and their `N`/`R`/`F` forms,
  `AND(`...`)`, `MPS`/`MRD`/`MPP`, `ST`/`STN`/`S`/`R`, `[ ... ]`
  operations, `BLK`...`OUT_BLK`...`END_BLK` blocks). Each output keeps its
  full path; paths share element objects wherever the IL shares a
  condition, so factoring common prefixes by identity rebuilds the grid
  shape. Block types come from the address prefix (`%TM` Timer, `%C`
  Counter, `%DR` Drum, `%WRITE_VAR` WriteVarBasic; one-to-one in every
  grid cell). All 94 IL rungs in the samples and the fixture's one convert
  and are equivalent to their IL by truth table; as a cross-check, the IL
  of 272 of the 278 grid rungs converts equivalently too (the other 6 use
  `RISINGn`/`MULTIFB`). Breaking the converter (OR as AND; ignoring
  MRD/MPP restore) is caught.
- [x] A: `LadderRung.instruction_list` (new model field) holds an IL rung's
  IL verbatim; it is the rung's only logic when B refuses
  (`instruction_list_not_converted`: `RISINGn`, `MULTIFB`, unbalanced
  brackets, unknown blocks). The PLCopen exporter then keeps the IL,
  readable, in the rung's comment (`instruction_list_rung_not_converted`).
  A grid rung's IL stays in its source extension only.

Every rung in the 63 samples now has a network (264 grid, 94 IL).

## Later

- Function-block parameters (`TimerTM` preset/base, counters, drums) joined
  to rung block references.
- `MastTask`/`FastTask` → `Task`, once scan-mode semantics are evidenced.
- Expansion modules and I/O configuration.
- `twinforge machine-expert-basic inspect` CLI, mirroring `scadapack inspect`.
- Real-world-scale samples: the current corpus is training exercises.
