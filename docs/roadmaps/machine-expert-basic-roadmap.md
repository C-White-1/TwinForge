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
- [x] Elements without a portable `LadderOperation` (edges, comparisons,
  operations, NOT, XOR, negative coils) stay in the network as `UNSUPPORTED`
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

## Later

- An IL representation in the model. IL-only rungs (91 in the samples) have
  no network and, since `text` is RLL, no model-level logic; their IL is
  only in source extensions. IEC 61131-3 IL is vendor-neutral, so this is a
  model decision, not a parser one.
- Function-block parameters (`TimerTM` preset/base, counters, drums) joined
  to rung block references.
- `MastTask`/`FastTask` → `Task`, once scan-mode semantics are evidenced.
- Expansion modules and I/O configuration.
- `twinforge machine-expert-basic inspect` CLI, mirroring `scadapack inspect`.
- Real-world-scale samples: the current corpus is training exercises.
