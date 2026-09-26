# Graphical diagram visualization roadmap

This roadmap covers rendering TwinForge's already-captured Ladder (LD) and
Function Block Diagram (FBD) evidence as an actual picture, not just a
navigable data model or a text report. It grew directly out of the Control
Expert ladder-resolution work: this project has spent real effort building
ad hoc, throwaway PIL scripts (never committed) to render a fixture's grid
back into an image purely to eyeball-verify parser output against a vendor
PDF. Making that a real, tested TwinForge capability turns a recurring
manual verification step into a reusable one, and gives users a way to see
an imported project's logic without owning the original vendor software.

## Objective

Render the vendor-neutral graphical model -- `GraphicalDiagram`,
`GraphicalObject`, `GraphicalPin`, and `LadderRung`/`LadderInstruction`
(`model/graphical.py`, `model/ladder.py`) -- as an SVG diagram, following
the same architectural pattern already established by
[`aoi_plantuml.py`](../../src/twinforge/exporters/aoi_plantuml.py): emit
deterministic **text markup**, not a rasterized image. No new image-library
dependency, no non-deterministic rendering step, output is directly
viewable (a browser opens SVG natively) and diffable in source control.

This renders the *model*, never raw captured XML directly -- consistent
with `AGENTS.md` ("avoid hard-coded XML parsing", "keep the model
vendor-neutral"). A renderer that reached back into `CapturedSection` to
read `posX`/`posY` itself would defeat the entire point of having a neutral
model in the first place, and would silently stop working the moment a
second source format (SCADAPack, CODESYS) needed the same capability.

## What the model already provides (verified, not assumed)

Checked directly against the current model and parser before writing this
roadmap, not assumed from memory:

- `GraphicalObject.position: LadderPosition | None` is already populated
  for any object with an `objPosition` child (`parsers/control_expert/
  graphical.py`) -- this covers `FFBBlock`s in both LD and FBD.
- `LadderRung.network` (a `LadderSeries` of `LadderInstruction`, each
  carrying its own `LadderPosition column/row`) already has full grid
  position for every resolved contact and coil in a pure-series LD row
  (`parsers/control_expert/ladder.py`).
- `LadderInstruction.operation == BLOCK_OUTPUT_REFERENCE` (shipped this
  session) already distinguishes "this condition comes from a named
  block's own output pin" from a plain tag read -- a renderer can draw
  that as a wire back to the block, not a floating unexplained label.
  Confirmed `+1 padding` output-row math is limited: this only resolves
  where a block's declared outputs are at least as many as its inputs
  (`enEnO="true"` blocks); an `inputs > outputs` block's output-side pins
  (`ADD`, `SR`, `INITCHART`, `SETSTEP`) are not placed by row at all yet.
- `GraphicalDiagram.links` (`GraphicalLink`/`GraphicalLinkEndpoint`)
  already resolves explicit FBD wiring by object/pin name, independent of
  position -- FBD connectivity does not depend on this roadmap's own
  position work at all.

What is **not** yet true, and matters for scoping below:

- ~~Contacts and coils only get a `LadderPosition` when they resolve as
  part of a *pure-series* `LadderRung`.~~ Resolved by Milestone 2:
  `GraphicalDiagram.grid_rows`/`LadderGridCell` now positions every
  contact/coil/block and every `HLink`/`VLink`/`shortCircuit` in an LD
  network, independent of whether the row also resolves as a
  `LadderRung`.
- FBD's `objPosition posX`/`posY` are free-canvas pixel offsets, not LD's
  grid cells -- the same `LadderPosition` dataclass currently holds both,
  which is a real semantic overload worth deciding on (a distinct pixel-
  position type, or a documented dual meaning) before an FBD renderer is
  built, not after.
- Nothing in the model currently tells a renderer a network's own
  declared width (`LDSource nbColumns`, `FBDSource nbRows`/`nbColumns`) --
  confirmed 100% consistent (`nbColumns="11"`) across every Control
  Expert LD fixture examined so far, but not currently retained on
  `GraphicalDiagram` itself.
- `LadderRung` still carries no network-index field (`LadderRung.number`,
  the row, resets to 0 for every `networkLD` the parser walks). This no
  longer matters for rendering: Milestone 2's CLI renders
  `Routine.graphical_diagrams` directly, and each `GraphicalDiagram`
  already knows which network it is, so the Milestone 1 workaround
  (grouping consecutive rungs by shared `SourceExtension.xml_path`) was
  removed rather than kept alongside the new path. The underlying gap
  would still matter to a *different* consumer of `LadderRung` directly
  (not through a `GraphicalDiagram`) -- not fixed at the model level,
  just no longer on this roadmap's own critical path.

## Milestone 1: LD grid rendering for pure-series rungs

- [x] Render a `LadderRung`'s series contacts and a trailing coil as
  standard IEC 61131-3 ladder symbols (open/closed contact, coil,
  reset/set coil) positioned by `LadderInstruction.position`, left rail
  to right rail (`exporters/ladder_svg.py`, `LadderSvgExporter`)
- [x] Render `BLOCK_OUTPUT_REFERENCE` as a labeled dashed box carrying the
  originating block's own `"instance.pin"` name, not a bare operand
  string. Still owed: an actual drawn wire back to the block symbol
  itself -- deferred to Milestone 2, since Milestone 1 doesn't render
  `FFBBlock`s at all yet, so there is no block symbol to wire back to
- [x] One `<svg>` per `networkLD`, laid out top-to-bottom by row.
  Confirmed against a real multi-network fixture
  (`Escalier_Mecanique.XEF`, 3 `networkLD` elements across 2 routines):
  `LadderRung` carries no network-index field, so the CLI derives
  network boundaries from each rung's own `SourceExtension.xml_path`
  (consecutive rungs sharing the same parent path are the same network)
  rather than guessing from row-number resets alone
- [x] CLI surface: `twinforge control-expert render <file> --output <dir>
  [--routine NAME] [--network N]`, consistent with the existing
  `inspect`/`coverage` subcommands -- writes one SVG per rendered
  network (`cli/control_expert_render.py`)
- [x] Deterministic output: identical input always produces byte-identical
  SVG (`test_ladder_svg_export.py::test_export_is_deterministic`), the
  same guarantee `aoi_plantuml.py` already provides

## Milestone 2: rows the model does not yet position -- done

- [x] Decided and implemented: extended the model generally, not a
  source-extension fallback. `GraphicalDiagram.grid_rows`/`LadderGridCell`
  (`model/graphical.py`) positions every contact/coil/block AND every
  `HLink`/`VLink`/`shortCircuit` in an LD network, computed by a new
  `compute_ld_grid()` (`parsers/control_expert/ladder.py`) that reuses the
  identical row/column rules already tested elsewhere in that module. See
  the LD grid geometry checkpoint
  (`docs/development/control-expert-checkpoints.md`).
- [x] `FFBBlock`s render inline (`LadderSvgExporter.export_diagram`,
  `exporters/ladder_svg.py`), reusing the confirmed 2-column width and
  `posY+1+i` pin-row math -- generalized to inputs too (already shipped
  separately for `TON.IN`-style later inputs, see the block-to-block
  chaining checkpoint) and to `enEnO="false"`'s own hidden-EN/ENO offset
  (free-standing vs shortCircuit-wrapped). Numerically verified against
  the real fixture, not just visually: `TON_23.IN`'s rendered Y position
  matches `posY+1+1` exactly, `SR_2`'s rendered box height matches its
  confirmed 3-row span exactly. Per this roadmap's own non-goal below,
  wire routing for `shortCircuit`/bare `VLink` is deliberately simple (one
  vertical connector per row, not the precise multi-segment corner
  placement a real ad hoc verification script worked out) -- pin ROW
  placement is not a styling choice and is not simplified.
- [x] CLI switched to render `Routine.graphical_diagrams` directly
  (`cli/control_expert_render.py`) -- each `GraphicalDiagram` already
  knows which network it is, so the Milestone 1 `_group_rungs_by_network`/
  `_network_key` workaround this roadmap flagged as fragile is gone
  entirely, not just left in place alongside the new path.
- Still open, not attempted this pass: `R` on an `enEnO="false"` block
  and `inputs > outputs` shapes' outputs remain genuinely unresolved (no
  positive example in the corpus) -- rendered as declared-but-unwired
  pins with no drawn condition, same honesty as the connectivity model
  itself, not hidden or guessed at.

## Milestone 3: FBD rendering

- [ ] Resolve the `LadderPosition` pixel-vs-grid overload noted above
  before writing any FBD-specific layout code
- [ ] Render `GraphicalObject`s by their own `posX`/`posY`/`width`/
  `height`, with `GraphicalLink`s drawn as explicit wires by resolved
  endpoint -- FBD's own connectivity is already fully resolved
  independent of position, so this milestone is materially lower-risk
  than Milestone 1/2's LD position gaps
- [ ] Cross-check against a fixture with real, non-trivial FBD content
  once the encoding is decoded far enough to have real position data to
  render (see the SCADAPack investigation notes:
  `docs/architecture/scadapack-rcz-format.md` -- most FBD evidence
  gathered there so far is string-level, not yet full object-graph
  decoding with real positions)

## Explicit non-goals

- Pixel-perfect replication of Control Expert's own rendering (fonts,
  exact spacing, colour scheme). The goal is a correct, readable
  diagram for verification and viewing, not a vendor UI clone.
- Editing. This is a read-only export, the same direction every other
  exporter in this project runs.
- Any raster image dependency (PIL, Cairo, etc.) inside the shipped
  package. Ad hoc raster scripts remain fine for one-off scratchpad
  verification work; the shipped capability stays text-in, text-out.

## Verification

Render every fixture already in the reference corpus and spot-check
against source; for Control Expert specifically, this project already has
several real vendor PDF renderings on hand (from the `sayahali/conveyor-
automation` investigation) to compare a rendered LD network against,
beyond just re-deriving the same grid math the parser itself already
uses.
