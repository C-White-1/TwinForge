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

- Contacts and coils only get a `LadderPosition` when they resolve as part
  of a *pure-series* `LadderRung`. A row diagnosed `unresolved_ladder_row`
  (`shortCircuit`/`VLink`/`FFBBlock` present) carries no per-element
  position in the model today -- only the raw retained source extension.
  Rendering such a row faithfully needs either new model fields or a
  fallback to source-extension-derived position, not yet decided here.
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

## Milestone 1: LD grid rendering for pure-series rungs

- [ ] Render a `LadderRung`'s series contacts and a trailing coil as
  standard IEC 61131-3 ladder symbols (open/closed contact, coil,
  reset/set coil) positioned by `LadderInstruction.position`, left rail
  to right rail
- [ ] Render `BLOCK_OUTPUT_REFERENCE` as a labeled wire back to the
  originating block's own instance name, not a bare operand string
- [ ] One `<svg>` per `networkLD`, laid out top-to-bottom by row; verify
  against the `nbColumns="11"` constant already confirmed across the
  whole real corpus
- [ ] CLI surface: `twinforge control-expert render <file> --network N
  --output out.svg` (exact flags TBD), consistent with the existing
  `inspect`/`coverage` subcommands
- [ ] Deterministic output: identical input always produces byte-identical
  SVG, the same guarantee `aoi_plantuml.py` already provides

## Milestone 2: rows the model does not yet position

- [ ] Decide and implement how an `unresolved_ladder_row` (branch/link/
  block wiring not evidenced) is rendered -- likely as its retained
  source extension's raw grid coordinates recovered on demand, or by
  extending the model to carry per-element position generally, not only
  for resolved pure-series rows
- [ ] Render `FFBBlock`s inline using `GraphicalObject.position`/`width`/
  `height` and their `GraphicalPin`s, reusing the confirmed 2-column
  width and `posY+1+i` output-row math from the block-output-reference
  work where it applies, and leaving pins it does not resolve (`R` on an
  `enEnO="false"` block, `inputs > outputs` shapes' outputs) visibly
  unresolved rather than guessed at

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
