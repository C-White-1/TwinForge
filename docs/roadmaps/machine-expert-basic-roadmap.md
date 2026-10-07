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
```

An independent package, following the per-format convention of
`parsers/control_expert/` and `parsers/scadapack/` (each format owns its
capture layer). Element names and paths come from
`schema/machine_expert_basic/`, not from the parser code.

Tests use small synthetic `.smbp` documents written in the test files. The
downloaded samples in `reference/machine-expert/` are mostly unlicensed and
stay local; they are used only for manual verification.

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
    in `metadata["source_memory_address"]`, the same key Control Expert uses;
  - each POU → a `Program` holding one `Routine` (`LD` if any rung has grid
    cells, else `IL`);
  - each rung → a `LadderRung` with `number`, `comment` (`MainComment`) and
    `text` (the IL lines, newline-joined); the whole `RungEntity`, grid
    cells included, is retained as a source extension.
  - `CryptedProject` → a controller named from `PublicProperties`, with an
    `encrypted_project` diagnostic and no logic.
- Not in this milestone: `LadderRung.network`, function-block parameters,
  tasks, expansion modules, CLI.

Password fields are retained in the captured tree (the capture is lossless)
but are never mapped into the model.

## Milestone 2: ladder networks from the grid

Build `LadderRung.network` (`LadderSeries`/`LadderParallel` of
`LadderInstruction`) from grid cells using the rules verified against IL in
the format specification. Planned acceptance check: every rung's network
must be equivalent to its IL, as `examples/check_smbp_grid_vs_il.py`
already shows for the wiring. Rungs whose grid is not series-parallel, or
that contain elements without a portable `LadderOperation`, get a
diagnostic and no network rather than a guessed one.

## Later

- Function-block parameters (`TimerTM` preset/base, counters, drums) joined
  to rung block references.
- `MastTask`/`FastTask` → `Task`, once scan-mode semantics are evidenced.
- Expansion modules and I/O configuration.
- `twinforge machine-expert-basic inspect` CLI, mirroring `scadapack inspect`.
- Real-world-scale samples: the current corpus is training exercises.
