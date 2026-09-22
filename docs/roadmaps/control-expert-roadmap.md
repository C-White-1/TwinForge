# Control Expert / Unity Pro import roadmap

Updated: 2026-09-20.

Objective: turn XEF/ZEF project evidence into useful vendor-neutral engineering
models while preserving all original content and explicitly reporting unresolved
semantics. Native re-import, compilation and runtime equivalence are separate
milestones, not consequences of successful XML parsing.

This roadmap owns delivery status and next work. The
[capture and mapping specification](../architecture/control-expert-exchange-capture.md)
owns observed structures, mapping decisions and evidence references. Update both
when capability changes; completed work below refers to the current working
tree, not a published release.

## Current capability

```powershell
uv run twinforge control-expert inspect reference\control-expert\function15.zip
uv run twinforge control-expert inspect reference\control-expert\function15.zip --format json
uv run twinforge control-expert coverage reference\control-expert\Escalier_Mecanique.XEF --output out\
```

TwinForge can inspect standalone XEF, ZEF and distribution ZIP files without a
Control Expert installation. It retains separate projects rather than merging
standalone and embedded exports. Reports describe captured evidence and partial
models; they do not certify executable conversion.

## Milestone 1: reference corpus and specification — complete for initial set

- [x] Inventory five user-supplied Schneider example ZIPs with SHA-256 hashes
- [x] Record nested members, exporter identities, project structure and provenance
- [x] Keep downloaded material and generated reports in ignored `reference/`
- [x] Record mismatched filenames and the differing XEF/ZEF projects in one ZIP
- [x] Distinguish observed grammar, documented rules and proposed mapping
- [x] Correct root distinction: standalone `FEFExchangeFile`, embedded `ZEFExchangeFile`

Evidence boundary: Quantum and Premium samples exported by Unity Pro 8.0, 8.1
and 10.0, plus a Control Expert V15.0 Premium escalator XEF/ZEF pair, all with
DTDVersion 41. There is no demonstrated coverage of every project carrying that
marker or of current Control Expert versions.

- [x] Inventory the escalator XEF/ZEF pair and compare its two SFC subtrees
- [x] Record observed steps, actions, transitions, alternative branch and return links
- [x] Specify and map root-level SFCProgram sections and retain chart-local transition sources
- [x] Add independent SFC fixtures before implementing graph connectivity or execution
- [x] Resolve chart-local transition references with missing/duplicate-target diagnostics
- [x] Bind observed explicit SFC link endpoints by type and exact lexical position within each network
- [x] Establish SFC adjacency/branch grammar before resolving complete connectivity
      (linear grid adjacency plus `altBranch`/`altJoint` selective divergence and
      convergence; see the connectivity checkpoint below for scope and limits)
- [x] `jumpSFC` (named jump to a step): a real fixture surfaced (see the
      `jumpSFC` checkpoint below); resolves like `alternative_join`, onward
      to the step it names, within the same network only
- [ ] Backlog: `parBranch`/`parJoint` (simultaneous/AND branching) grammar.
      Still documented only by a third party's own reverse-engineering
      (`apexsotjo-blip/control-expert-mcp`'s `lang_reference.py`), never
      observed in an actual export, including the new real fixture below (it
      only uses `altBranch`/`altJoint`, already supported). Do not implement
      from that description alone; wait for a real fixture, the same
      standard applied to every other element here.

The new pair has matching SFC subtrees: five steps, six transitions and ten
actions. Inspection now maps all six sections and resolves both SFC task references.
Neutral chart trees retain ordered objects, lexical coordinates and local ST
definitions; connectivity and execution remain unresolved. Local transition references now
bind to unique definitions within their source section, with case-insensitive
identity and missing/duplicate diagnostics. Timer-member expressions remain unbound. See the
capture specification's additional SFC specimen section for evidence and limits.

Additional corpus: the multi-Grafcet XEF/ZEF pair maps eight sections, including
three SFC charts (ten steps, ten transitions, eleven actions). It adds periodic
MAST, timer-member conditions, `NONE` action qualifiers and cross-chart control
calls. Both exports identify Premium despite the repository's M580 description.

- [x] Inventory and inspect the multi-Grafcet pair; retain provenance discrepancy
- [ ] Specify periodic task timing from authoritative evidence
- [ ] Resolve timer-member and step-state expressions without simple-name assumptions
- [ ] Account for chart-control calls and multiple writers before execution claims

## Milestone 2: lossless capture — initial implementation complete

- [x] Retain original input and expanded member bytes, hashes and ordinal identity
- [x] Preserve duplicate member names, directories and opaque data
- [x] Capture XML attributes, child order, text, tails and unknown content
- [x] Preserve exact lexical source through retained bytes
- [x] Bound input/expansion sizes, archive depth/member count and XML depth/elements
- [x] Diagnose corrupt, encrypted, unsupported and limited capture explicitly
- [x] Reject DTD declarations without external entity resolution
- [x] Keep original parent archives when individual members cannot be read

Completion criterion met for the initial corpus and synthetic failure fixtures.
Limits can intentionally leave members unexpanded; these cases are not reported
as complete inspection. Capture does not yet validate against Schneider XSDs.

## Milestone 3: basic neutral mapping and inspection — initial subset complete

- [x] Map project identity, controller identity and observed rack/module layouts
- [x] Preserve special/conflicting module positions as unplaced hardware
      (with one refinement: a power supply is now its own resolved concept,
      not folded into "unplaced" -- see the power supply checkpoint below.
      This is evidenced only for the Schneider ATS rack layout's own distinct
      `powerSupply` tag; other manufacturers mount power supplies differently
      -- some in-chassis, some not -- and nothing here generalizes across them)
- [x] Map variable names, type expressions, comments and source address evidence
- [x] Preserve array bounds and initializers without inventing type/value semantics
- [x] Map task configuration, section ordering, programs and ST source
- [x] Resolve section references with case and identity-conflict diagnostics
- [x] Record cyclic scheduling separately from block enable/evaluation conditions
- [x] Retain complete source extensions and location-bearing diagnostics
- [x] Expose deterministic text/JSON inspection through the installed CLI
- [x] Return a failure status for incomplete capture or no supported projects

Completion criterion met: all five embedded projects reconcile to the inventory's
variable and section counts. Unsupported hardware and unresolved types remain
visible. Initial values are lexical evidence, not promoted typed values.

## Milestone 4: graphical structure and references — partial

- [x] Extract observed FBD/LD blocks, pins, contacts, annotations and explicit positions
- [x] Distinguish source pin direction, expression binding and EN/ENO roles
- [x] Retain execution override hints without assuming their reference grammar
- [x] Resolve relative order for the supported single-block FBD network case
- [x] Resolve multi-block FBD order from verified vendor rules: a documented
      Schneider FAQ (FA340273), generalized from its worked 2-level example to
      a full topological sort for deeper chains (real chains up to 7 levels
      exist in the corpus) -- see the documented dependency order checkpoint
      below for the exact scope and what's still an extrapolation, not
      separately vendor-confirmed
- [x] Resolve simple declared-variable pin expressions case-insensitively
- [x] Classify supported lexical literals, unbound pins and unresolved expressions
- [x] Group shared-variable references without inventing graphical wires
- [x] Preserve ambiguous declarations instead of binding to the first occurrence
- [x] Capture and validate library block interfaces against actual calls
- [x] Resolve LD contact step-state member expressions against declared SFC steps
- [ ] Resolve indexed and other member expressions using proven type definitions and bounds
      (partial: proven paths resolve -- see the member path, resource variable,
      Device DDT catalog and Tier 1/2 binary expression checkpoints below;
      chained same-operator expressions and inline function/EF calls remain
      unresolved on purpose -- see the Tier 2 checkpoint's explicit exclusions)
- [x] Interpret explicit FBD links/connectors with endpoint diagnostics
      (`GraphicalDiagram.links`, resolved by object-instance/pin name, not
      position; see the explicit FBD link checkpoint below -- this is
      connectivity only, not an execution-order claim)
- [x] Decode Ladder grid connectivity for the pure-series case (contacts in
      series to one trailing coil, per row); see the Ladder series checkpoint
      below for scope
- [x] Resolve `shortCircuit`/`VLink` vertical wires that land cleanly on a
      target `FFBBlock`'s `EN` pin (the only pin ever evidenced as a
      target); see the `shortCircuit`/SCE checkpoint below. This is
      deliberately narrower than Schneider's documented Short Circuit
      Evaluation bypass semantics, which no fixture in the corpus proves
      applies here -- structural connectivity only, not synthesized
      bypass-and-passthrough execution.
- [ ] Backlog: the remaining ambiguous `shortCircuit`/`VLink` shape -- a wire
      that keeps a `VLink` alive one row past a candidate landing (real
      example: `MBP_MSTR_7` in `function15.zip`/`function2.zip`), which may
      mean a second input row is fed the same way, or may just be a
      multi-row block's own border rendered with the same element. Not
      decidable from the grid alone; needs either more fixtures or vendor
      documentation of the row-to-pin mapping for multi-row blocks.
- [x] Resolve multi-block/network order under link and override rules: explicit
      links are covered above; `execAfter` is now an extra dependency edge, an
      inference not vendor-documented -- see the `execAfter` checkpoint below
- [ ] Interpret section conditions, enable behavior, jumps and other control flow
      (partial: section `activationCondition`/`logicCondition` captured as
      lexical evidence -- see the section condition checkpoint below; nothing
      is evaluated, and enable behavior and jumps remain open)
- [ ] Produce executable neutral graph/IR only for a verified semantic subset
- [x] `FBSource`/`FBProgram` (user-defined Function Block definitions): interface,
      locals and body captured into the existing `AddOnInstruction` model, and
      also registered as a `user_function_block` library interface for call
      validation at instantiation sites. See the DFB capture checkpoint below
- [x] Bind pins/symbols inside an FB body against that FB's own isolated
      parameter/local namespace, never the project's flat global tags (IEC
      61131-3 encapsulation) -- see the FB-local binding checkpoint below

Completion criterion: connections and ordering are supported by a documented
grammar plus discriminating fixtures. Task scans, section order, block order and
block enable conditions must remain separate. Shared names are not wires, and
source pin direction alone does not prove memory read/write effects.

## Next implementation: block interfaces and call validation

The samples already contain EFSource/EFBSource interface descriptions. Use those
as evidence for the next bounded step without requiring a vendor installation:

1. Extend the declarative specification for library identity and ordered
   input/output parameter definitions, retaining unknown interface metadata.
2. Represent interface evidence separately from executable implementations;
   imported library signatures are not user-defined function-block bodies.
3. Match graphical calls to unique definitions with case-insensitive identity,
   reporting missing or ambiguous definitions and unmatched pins.
4. Handle repeated input/output names, generic types, extensible parameters and
   implicit EN/ENO explicitly. Do not reject a call merely because the current
   profile cannot interpret a library convention.
5. Add the resulting interface/coverage evidence to CLI inspection and tests.

Acceptance: real MBP_MSTR, TON, ADDR and READ_VAR signatures are inspectable;
synthetic mismatches are diagnosed; no block execution or datatype compatibility
is claimed from a matching name alone. Existing capture and reference behavior
must remain unchanged.

## Milestone 5: broader type and source coverage — partial

- [ ] Promote a documented subset of scalar initial values with lexical provenance
- [x] Model array lower bounds without zero-base loss, for DDT members
      (`DatatypeMember.dimension` retains the lexical `lower..upper` text
      unchanged, e.g. `"257..384"`, deliberately not renumbered from zero);
      composite (struct/array) *initialization* is a separate, still-pending
      concern -- see the DDT capture checkpoint below for scope
- [x] Capture DDT definitions and cross-references (`DDTSource`, including
      forward references between DDTs) and custom DFB definitions
      (`FBSource`/`FBProgram`, interface/locals/body -- see the DFB capture
      checkpoint below); device DDT remains a distinct, still-pending
      mechanism, not yet found in any local fixture
- [ ] Distinguish library types, block-instance types and user-defined data types
- [ ] Extend ST analysis with source dialect/system-address evidence
- [ ] Add SFC, IL/LL984 and additional task/hardware forms as evidence becomes available
- [ ] Add populated DTM and modern M580/Control Expert examples (a real,
      populated Control Expert V14.0 M580 **safety** project is now in the
      corpus -- see the explicit FBD link and power supply checkpoints above
      -- but its `DTMConfiguration` content specifically has not been surveyed)
- [ ] Characterize encrypted/protected exports and retain unsupported content
      (`FBSource/crypted` in the M580 safety fixture is confirmed genuinely
      opaque hex-encoded evidence, 7 occurrences; not yet wired into capture)

No inferred DTDVersion-to-release table: preserve the marker alongside exporter
identity and actual feature coverage.

## Planned: multilingual identifiers and comments

Motivation: the M580 safety project already proved real tags use French
accented letters (é/è; see the accented identifier checkpoint above), and a
Spanish-authored ZEF export is expected next. Deferred here rather than
implemented now -- explicitly requested to wait rather than build ahead of
the evidence.

- [ ] Broaden `ExpressionSpec.identifier`'s accented-letter allowance from the
      two evidenced French characters to a general Unicode-letter class,
      *ahead of* per-language fixture evidence -- a deliberate policy change
      from how every other identifier fix in this roadmap proceeded (each
      widened only after a real corpus occurrence). The reasoning: waiting
      for a dedicated investigation each time a new language's tag names
      surface (as the French checkpoint required) does not scale across
      many languages the way it does for one. Still undecided before
      implementing: exactly which Unicode category/block to accept (all
      Unicode letter categories? Latin-1 Supplement + Latin Extended-A,
      covering most Western European languages? something broader still,
      e.g. Cyrillic/Greek?), and re-confirming it does not weaken the
      numeric-literal/bit-select exclusion the identifier grammar depends on
      (a purely-digit token must keep failing to match, exactly as the
      digit-led KKS fix already guards for).
- [ ] Detect the dominant language of a project's free-text fields (comments,
      descriptions, action/step names, annotations) as an informational
      diagnostic -- metadata only, no effect on capture, resolution, or the
      captured text itself. Needs a decision on mechanism (a lightweight
      heuristic vs. a real dependency) and on where the result surfaces (CLI
      inspection output, or a new non-blocking `Diagnostic` code).
- [ ] Translate captured comments/descriptions to English into a *separate*
      log, never altering the captured source text (the same "never discard"
      principle already governing everything else this project captures):
      one entry per translated field, keyed by the element's existing
      `SourceLocation`, recording the detected source language, the original
      text and the English translation, id in brackets (e.g. `[id] es -> en:
      "<original>" -> "<translation>"`). Needs a translation mechanism (the
      project depends on none today) and a decision on where the log is
      produced (a new CLI subcommand's output file, or a section of the
      existing JSON inspection report).

Blocked on: a real non-French-language fixture (the expected Spanish ZEF)
before the first item is implemented from more than a policy decision alone;
a concrete choice of translation mechanism/dependency for the third.

## Milestone 6: schema, editor and runtime validation — pending external evidence

- [ ] Obtain a versioned Schneider SrcXmlSchema set and all dependencies
- [ ] Obtain authoritative documentation of DTDVersion and compatibility
- [ ] Validate representative exchange XML against the corresponding schema set
- [ ] Establish access to a Control Expert validation environment
- [ ] Record native import and build outcomes separately from capture results
- [ ] Validate any generated exchange output by native re-import/build
- [ ] Compare runtime behavior for a deliberately small executable subset
- [ ] Publish per-fixture compatibility claims with versions and limitations

The user currently has no Control Expert installation. This does not block
offline capture, reference resolution or interface work. No support request has
been sent, no installation purchased, and no native validation performed.

## Verification and maintenance

Portable fixtures are independently authored; local-reference tests skip
explicitly when the ignored source files are unavailable.

```powershell
uv run pytest tests/test_control_expert_sfc.py tests/test_control_expert_capture.py tests/test_control_expert_project.py tests/test_control_expert_graphical.py tests/test_graphical_bindings.py tests/test_cli_control_expert.py tests/test_model_json_export.py tests/test_sfc_connectivity.py tests/test_sfc_coverage.py tests/test_control_expert_ladder.py tests/test_control_expert_datatypes.py tests/test_control_expert_function_blocks.py tests/test_execution_order.py
```

Run Ruff and Pyright on changed modules, plus relevant model/CLI/ST regressions
when shared contracts change. Use a fresh workspace-local `--basetemp` if the
existing pytest artifact directory is locked. Recheck archive hashes after
reference operations. Avoid making third-party archives mandatory CI inputs.

The last full run of the command's test set passed 61 tests, including optional
local samples; Ruff and Pyright passed. This is a dated development checkpoint,
not a substitute for running the checks after future changes.

For each milestone, record code, independent tests, source evidence, open
limitations and user-facing documentation together. Do not mark graphical
execution or vendor compatibility complete based only on successful capture.

Latest SFC reference checkpoint: 36 targeted SFC/project/CLI/model-export tests
passed, including both local reference pairs; Ruff and Pyright passed. All four
escalator transition references resolve in each export. Multi-Grafcet timer-member
expressions remain lexical evidence, not chart-local definition references.

Explicit-link checkpoint: all six recorded endpoints resolve in each of the four
local SFC exports. Endpoint paths address chart element/network-child indices.
Missing or ambiguous endpoints and unsupported types remain diagnosed; layout
adjacency, branch semantics and complete connectivity remain unresolved.
42 targeted tests passed; Ruff and Pyright passed.

SFC symbol checkpoint: simple action-target and transition-variable references
now bind to unique declared tags with ambiguity diagnostics. All twelve escalator
occurrences and fifteen multi-Grafcet occurrences bind per export; the six
multi-Grafcet timer-member expressions remain unresolved. Independent tests cover
missing and duplicate declarations, lexical preservation and stale-binding reset.
43 targeted SFC/project/CLI/model-export tests passed; Ruff and Pyright passed.
Next: library/type evidence needed for timer-member and step-state resolution;
full connectivity and execution remain pending.

Library/member checkpoint: EF/EFB signature evidence is now exposed in parsed
projects and CLI JSON. Six TON.Q references resolve in each multi-Grafcet export
through unique declared instance/interface/member identities. Earlier unresolved
member counts are historical checkpoints. Graphical call validation, generic and
extensible parameters, step-state types and executable library behavior remain
pending. 45 targeted tests passed; Ruff and Pyright passed.

Graphical interface checkpoint: unique block types and name/direction pin matches
are now inspectable, with diagnostics for absent/ambiguous definitions and
unmatched data pins. Implicit EN/ENO pins are distinguished. Generic/extensible
parameter rules, missing-required-pin checks and datatype compatibility remain
pending; interface identity alone is not call validation. 54 targeted tests passed
before the final non-block filtering refinement; lint and type checks passed.

Final non-block filtering verification: 15 library-call, graphical and CLI tests
passed; all local corpus inspection reports refreshed.

Extensible-parameter checkpoint: numbered pins on Schneider's extensible EF
templates now resolve using the vendor's own `(Extensible)` comment marker
(observed on `ADD`'s `IN1`, paired with a hidden `nin` count parameter), never
a name-pattern guess applied without that evidence. Both `IN2` pins in each of
`function15` and `function2` now resolve `matched_extensible` instead of
`unresolved_convention`; a base shared by more than one marked template is
`ambiguous`. Generic types, in-out representations and datatype compatibility
remain unverified. 76 targeted tests passed; Ruff and Pyright passed.

Multi-block FBD order correction (2026-09-21): the earlier shared-variable
ordering inference is withdrawn. A disconnected graph could be marked resolved
with an arbitrary reversed order; even a unique shared-variable chain does not
prove vendor execution order. Multi-block order now remains unresolved while
shared symbol groups are retained. Legacy inferred order is cleared on reruns;
single-block evidence is preserved. Explicit link/layout/override rules still
require independent evidence. The specification describes the regression cases.

LD contact binding checkpoint: contact operands previously carried no binding
classification at all. Real evidence shows two shapes: plain declared-symbol
contacts (`Escalier_Mecanique`'s `BPA`, `Start_Timer`, ...) and Control
Expert's `<step>.X`/`.x` step-active-state convention, observed making
genuine cross-section references (`MultiGrafcet`'s `Init` LD section reads
seven step states declared in its separate `G1`/`G2`/`GMaitre` SFC charts). A
raw system-bit reference such as `%S1` correctly stays `unresolved_expression`
rather than being guessed. Step names are matched through a project-wide
registry (global, not chart-local — the evidence shows cross-section use and
no corpus duplicate contradicts it; a genuine duplicate is still reported
ambiguous). 88 targeted tests passed; Ruff and Pyright passed. Indexed
expressions have no corpus evidence yet and remain open, as do LD grid
connectivity and explicit FBD links.

In-out parameter checkpoint (2026-09-21): the explicit Control Expert profile
matches READ_VAR's input/output GEST pins to its single declared inout parameter.
Both pins remain independently represented. Four occurrences across the two
READ_VAR exports match, leaving no unresolved pin conventions in the local corpus.
Generic types, access semantics and required-pin validation remain pending.
56 targeted tests passed; Ruff and Pyright passed. Local reports refreshed.

SFC connectivity checkpoint (2026-09-21): a step or transition's successor now
resolves when exactly one candidate exists -- the unique flow object at the next
grid row in the same column, or a resolved explicit link sourced from it.
Divergence uses an `altBranch` element colocated with the first column's
transition; convergence uses a linked `altJoint`, resolved onward to whatever
follows its own anchor position. Both require `relativePos="0"`, the only value
evidenced anywhere in the corpus; any other shape, any incomplete branch row, and
any conflicting pair of candidates stays diagnosed (`unresolved_sfc_successor`,
`ambiguous_sfc_successor`, `unsupported_sfc_branch_position`) and unresolved
rather than guessed. `SequentialChart` gained `connectivity_edges`, exposed in
CLI JSON alongside `connectivity_resolved`; execution semantics remain untouched.

The linear-adjacency rule is now corroborated by three independently-authored
sources with no counterexample: the two PsyGlo repositories and a third,
unrelated origin (`IUT-GEII-Annecy/automatisme-pour-robotique`, French
university robotics coursework), whose `02_MAIN.sfc.xml` also supplied the
first concrete `altJoint` evidence and the first complete divergence/convergence
pair in one chart (kept in `reference/control-expert/`, see the capture
specification). Explicit link endpoint resolution was extended to match
`altBranch`/`altJoint` by width span from their own recorded position, not only
exact lexical equality, since a real link's destination coordinate need not
equal the branch/join's own position. Both real SFC exports already in the
corpus (escalator, multi-Grafcet: five charts total) now fully resolve with
zero connectivity diagnostics -- a regression check as much as a validation.
`parBranch`/`parJoint` and `jumpSFC` remain backlogged pending a real fixture
(see the Milestone 1 backlog item); nested/repeated branching, AND-convergence
and any topology beyond one branch/join pair are unevidenced and untested.
88 targeted tests passed (including both local reference pairs); Ruff and
Pyright passed; full suite (1192 tests) passed.

SFC test-coverage skeleton (2026-09-21): `twinforge control-expert coverage
<path> --output <dir>` writes one Markdown/CSV/JSON traceability skeleton per
parsed project -- one row per step, per transition (with its condition text
when it resolves to a simple reference) and per SFC-relevant diagnostic, each
correlated back to its owning program/routine/chart by exact source-location
match. Requirement ID, Test ID and Status columns are always present but
blank; this is a starting point for a reviewer's test matrix, not a record of
tests performed, and it does not certify the underlying PLC logic. Diagnostics
outside a defined SFC-relevant set (FBD, hardware, variable-type codes, ...)
are intentionally excluded -- see `SFC_DIAGNOSTIC_CODES` in
`analysis/sfc_coverage.py`.

Known limitation, not yet addressed: regenerating the skeleton overwrites it
rather than merging a reviewer's prior Requirement ID/Test ID/Status
annotations back in. The engineering-review overlay mechanism already used
for L5X alarm/cause-effect review (`review validate`, applied-key
reconciliation) would be the natural way to close this gap, but is
substantially more machinery (a versioned schema, validation, receipts) than
this pass adds; revisit only if the manual-CSV workflow proves insufficient
in practice. 7 targeted tests passed (unit, exporters, CLI round-trip and a
clean-error path); validated against both real escalator charts (5 steps, 6
transitions, 0 unresolved, 2 diagnostics -- both the unavoidable
per-routine execution-unresolved notice). Full suite (1199 tests) passed;
Ruff and Pyright passed.

Ladder series checkpoint (2026-09-21): `Routine.ladder_rungs` is now populated
for the pure-series case. Each `typeLine` under a `networkLD` is one grid row
(`emptyLine[nbRows]` advances the row counter without occupying one, verified
against real `FFBBlock`/`objPosition` row values); column is the cumulative
cell width consumed left to right (`emptyCell`/`HLink` by `nbCells`, a contact
or coil by exactly one cell -- neither carries its own coordinate). A row
resolves only when it holds nothing but contacts, wiring, and exactly one
coil as its last cell-bearing element -- an unambiguous series-AND rung, built
directly into the existing `LadderRung`/`LadderSeries`/`LadderInstruction`
model already used by the L5X/CCW/PLCopen converters, just never populated
from Control Expert until now. `coil` is newly mapped as a `GraphicalObject`
kind (previously fell through as `unclassified_graphical_object` for every
real coil in the corpus).

Any row touching `shortCircuit`, `VLink`, `FFBBlock` or `textBox` is
diagnosed (`unresolved_ladder_row`) and left unresolved, per the Milestone 4
backlog item above -- real evidence (`function15.zip`) showed a vertical wire
can span many rows to reach a distant block, a materially different and
harder problem than the adjacent-row branch merge first hypothesized from a
smaller example, so it was deliberately not attempted from two examples.
A row with contacts but no coil, or a coil that isn't the sole final element,
is diagnosed (`ladder_series_missing_coil` / `ladder_series_unexpected_coil_
position`) rather than guessed at; an unevidenced contact/coil type variant
(only `openContact`/`closedContact` and `coil`/`resetCoil` are witnessed)
still resolves structurally with `LadderOperation.UNSUPPORTED` and its own
diagnostic (`unresolved_ladder_instruction`), preserving the instruction as
evidence without claiming its boolean semantics.

Validated against the real escalator corpus: `Rising_Edge_Detection` (4/4
rows, pure series) fully resolves; `Init_Logic` resolves 2 of its rows (an
unconditional reset coil, and a plain contact-to-coil rung) and diagnoses the
rest (`INITCHART`-gating rows); `TIMERS` resolves none (a `TON` block row and
a contact row with no coil). The multi-Grafcet LD section (`INITCHART`/
`SETSTEP`/six `TON` instances, all branch/block-gated) resolves zero rungs,
exactly as expected -- nothing is wrongly resolved there. 14 targeted tests
passed (synthetic series/branch/edge cases plus both real corpus pairs). Full
suite (1213 tests) passed; Ruff and Pyright passed.

Coil operand binding checkpoint (2026-09-21): coil operands now resolve
through `resolve_graphical_bindings` alongside contacts (declared/missing/
ambiguous symbol, with their own `*_coil_*` diagnostic codes), but a coil
operand is never tested against the `<step>.X` step-state pattern even on a
lexical match -- a coil cannot legitimately write a step's active-state bit,
so that stays contact-only. All six real escalator coils resolve
`declared_symbol`. 7 targeted tests passed; full suite (1214 tests) passed;
Ruff and Pyright passed.

Explicit FBD link evidence check (2026-09-21): before attempting multi-block
FBD order (the natural next Milestone 4 item), the local corpus was checked
for any explicit graphical link element analogous to SFC's `linkSFC` or
Ladder's `HLink`/`VLink`. None exists: `readvar.zip`'s two-block `ADDR`/
`READ_VAR` diagram has no link element at all, only two `FFBBlock`s connected
solely by the shared `ipaddress` parameter name -- exactly the inference
already withdrawn as unproven. The `linkFB` element referenced in the
`apexsotjo-blip/control-expert-mcp` third-party notes has no corpus backing
either, the same standing as `parBranch`/`parJoint`/`jumpSFC` above. Multi-
block FBD order remains blocked on evidence, not on implementation effort;
do not attempt it from that description alone.

Explicit FBD link checkpoint (2026-09-21): the evidence gap above was closed
by a real, MIT-licensed fixture found from a different search
(`estradege/controlexpert`, a C#/.NET Control Expert interop library) --
`estradege_m580-safety.xef`, a genuine Control Expert V14.0 M580 **safety**
project with 32 FBD networks and 430 `linkFB` elements, now kept in
`reference/control-expert/` alongside a smaller `estradege_m340.xef`.
`GraphicalDiagram.links` resolves each `linkFB`'s source/destination by
(`instanceName`, `pinName`, implied direction) -- name identity, not grid
position, which sidesteps the coordinate-adjacency ambiguity that made SFC
and Ladder resolution harder. All 371 real `linkFB` occurrences resolve
cleanly on both ends; the `unclassified_graphical_object` diagnostic every
one of them produced before this change is gone for that project. This
explicitly does not claim execution order -- `linkFB` is materially stronger
evidence than the withdrawn shared-parameter-name inference, but "source
executes before destination" is a separate claim needing its own evidence
before being attempted, kept unresolved here on purpose (see Milestone 4).
17 targeted graphical tests passed (six new failure-mode cases plus both real
fixtures); full suite (1223 tests) passed; Ruff and Pyright passed.

Power supply checkpoint (2026-09-21): the M580 safety fixture's rack has a
`powerSupply` element (`BMXCPS4002S`) with `equipInfo position="-1"`, a
distinct vendor tag already separate from `moduleATS` in the source XML. The
first attempt at this treated `-1` as just another (negative) slot number --
mechanically defensible, since the parser's `position.isdecimal()` check
rejects the sign character and was silently dropping this real, consistent
value -- but an existing synthetic test showed that was already a *deliberate*
prior decision (leave a special position unplaced), not an oversight, and
the same case appears in the original `readvar.zip` fixture too. Widening the
parse to accept "-1" would have contradicted that decision for every existing
fixture, not just the new one.

The actual issue was model shape, not parsing: a power supply is not slot
addressed at all -- it mounts in its own position, physically separate from
the numbered rack scheme, not merely at an unusual slot number. `Chassis`
gained `power_supplies: list[Module]` and `add_power_supply()`, and
`HardwareLayout` gained `power_supply_modules: tuple[str, ...] = ()`, set to
`("powerSupply",)` only for the Schneider ATS layout, where the vendor's own
XML already draws that distinction; the Quantum layout (no such tag observed)
is untouched. A power supply with a resolvable identity now lands in
`chassis.power_supplies`, fully resolved and reported neither as a numbered
module nor as unplaced hardware; one with no identity still reports
`unplaced_hardware`, unchanged. This does not generalize across
manufacturers -- some mount power supplies in-chassis, some do not -- so the
distinction stays scoped to the one vendor tag shape that actually evidences
it. Both the M580 safety project (`BMXCPS4002S`) and the original
`readvar.zip` (previously silently dropped into `unplaced_modules`) now
resolve their power supply the same way. 2 targeted hardware tests
added/updated (9 total in `test_control_expert_project.py`); full suite
(1224 tests) passed; Ruff and Pyright passed.

DDT capture checkpoint (2026-09-21): `DDTSource` (a project-root sibling of
`program`, not nested under one) now maps to the existing, previously
entirely-unpopulated `Datatype`/`DatatypeMember` model -- greenfield, like
`LadderRung` before the Ladder series work. Datatypes are collected in a
first pass (so every name is known), then members in a second, so a member's
`typeName` can forward-reference a DDT declared later in source order;
resolving that reference sets `DatatypeMember.data_type` to the real
`Datatype` object, distinguishing a composite (nested-DDT) member from a
scalar one without conflating them. Array bounds reuse the array-bounds
regex already relied on for top-level tags, but land in the dedicated
`dimension` field as the raw `"lower..upper"` text (e.g. `"257..384"`),
deliberately not renumbered from zero -- exactly the loss the milestone item
warns against. Top-level tags (`_variables`) now also recognize a known DDT
name as a resolved type, not just the scalar set, since leaving a
now-captured DDT-typed tag permanently `unresolved_type` once its DDT is
known would be a straightforward, avoidable gap, not a new claim.

Real evidence surfaced a second, smaller gap: of the M580 safety fixture's
DDT members, 43 initially reported `unresolved_type` for `BYTE`/`UINT`/
`REAL`/`UDINT` -- genuine, unambiguous elementary IEC types absent from
`scalar_types`, not composite or vendor-specific types. `BYTE`, `REAL`,
`EBOOL` (Schneider's extended-BOOL, still elementary), `DWORD`, `UDINT` and
`UINT` were added; generic placeholder types (`ANY`, `ANY_NUM`, `ANY_BIT`,
...) and FB/EFB instance type names (`TON`, `SFC_TRAN`, `S_SR`, dozens of
others, all in the same corpus but structurally unrelated to DDT member
typing) were deliberately left alone -- neither is a scalar value type.

The `SAFE` task found during the earlier survey needed no new code at all:
its `taskDesc` carries `taskType="periodic"`, a value the existing generic
(name-agnostic) task-scheduling logic already handles identically to the
multi-Grafcet corpus's periodic MAST task; only its *name* ("SAFE") is new.
All 13 real DDTs resolve; `T_BMENOC0321` (5 array members, 1 nested-DDT
reference to `T_NOCDIO_HEALTH`) is checked directly. 8 targeted datatype
tests passed; full suite (1232 tests) passed; Ruff and Pyright passed.

DFB (user-defined Function Block) capture checkpoint (2026-09-21):
`FBSource` maps to the existing `AddOnInstruction`/`AddOnInstructionParameter`
model -- unpopulated for Control Expert until now, the same shape Rockwell
AOIs already use, and a natural fit: a DFB genuinely is "a reusable
instruction with parameters, local tags and an implementation," not a new
concept requiring its own model. All 83 real definitions in the M580 safety
fixture resolve: interface parameters (`inputParameters`/`outputParameters`/
`inOutParameters`, direct children when the body is real, nested under
`ExternalToolsOnly` when `crypted` -- the two locations are mutually
exclusive, reusing the same `library_parameters` path list rather than
adding a second lookup mechanism), local variables
(`publicLocalVariables`/`privateLocalVariables` into `local_tags`, kept
separate from the external parameter interface, matching the AOI model's own
separation) and a body: `STSource` (65) or `FBDSource` (10) parsed exactly
as a top-level program's would be, reusing `parse_diagrams`/structured-text
line-splitting unchanged. 7 are `crypted` (interface retained, body
genuinely opaque, diagnosed `encrypted_function_block_body`); one
(`IO_AI_EX`) has two `FBProgram` elements -- diagnosed
`ambiguous_function_block_body` rather than guessed, the same discipline
applied to every other multi-match case in this parser.

Parameter and local-variable types now resolve against the DDT registry
built earlier the same pass (`data_type_definition`), and -- since the
registry already existed -- top-level tags gained the same resolution as a
direct, low-risk completion of the earlier DDT checkpoint (it had suppressed
the `unresolved_type` diagnostic for a DDT-typed tag but never actually set
`Tag.data_type_definition`, an oversight caught while implementing this).

Each DFB is also registered as a `user_function_block` library interface
(alongside the existing `EFBSource`/`EFSource` vendor-library entries),
letting the already-built `match_library_calls` validate calls to
project-defined FBs the same way it validates vendor-library calls -- a real
gap closed for free, since 260 real `FFBBlock` instances in this project's
own top-level programs call a user-defined FB, previously left entirely
unrecognized (`unclassified`/`unresolved_library_interface`).

Deliberately not attempted: resolving pins/symbols *inside* an FB body. An
FB body's parameters and locals form their own namespace, not the project's
flat global tag table the existing `resolve_graphical_bindings`/
`resolve_sequential_bindings` assume -- wiring FB routines into those passes
without FB-local scoping would produce wrong bindings, not just incomplete
ones, so it stays a separate, explicitly deferred step. Device DDT
definitions also remain unaddressed -- a distinct mechanism from
`DDTSource`, not yet found in any local fixture. 11 targeted tests passed
(synthetic interface/body/locals/diagnostics cases, a call-validation
round-trip, and the full real fixture); full suite (1243 tests) passed;
Ruff and Pyright passed.

FB-local binding checkpoint (2026-09-21): the deferred step above is done.
`resolve_graphical_bindings`'s core per-diagram resolution logic (contact/coil
operand binding, pin binding, shared-variable grouping) was extracted into a
private `_resolve_diagrams` helper reused by two public entry points --
`resolve_graphical_bindings` unchanged (project-global `controller.tags`) and
a new `resolve_function_block_bindings`, which builds one *isolated* symbol
table per `AddOnInstruction` from only that FB's own `parameters` and
`local_tags`, resolved once per FB, never mixed with the project's globals
or another FB's namespace -- proven directly: two FBs each declaring a
parameter named `IN`, wired to two separate pins, resolve independently to
each FB's own parameter, and a global tag sharing a DFB's unresolved pin's
name is deliberately *not* used as a fallback (IEC 61131-3 encapsulation,
not an evidence gap).

Only FBD bodies have anything to bind -- ST bodies are retained as plain
text, not parsed into pin/expression structure at all, so this applies to
10 of the 83 real DFBs, not all of them. `GraphicalPin` gained
`target_parameter: AddOnInstructionParameter | None`, set instead of (never
together with) `target_tag` when a pin resolves inside an FB body -- a
resolved `AddOnInstructionParameter` is not a `Tag`, so reusing `target_tag`
would have been a type error disguised as a shortcut, not a simplification.
Real FBD-bodied DFB pins in the M580 safety fixture resolve cleanly against
their own parameters (e.g. `M_DWORD_TO_BIT`'s inner `WORD_TO_BIT.BIT16` pin
resolves to the outer DFB's own `BIT16` output parameter); complex
expressions (`GEST[1].0`, `Communication = 16#00`,
`UDINT_TO_TIME(1000 * HoldupTime)`) correctly stay `unresolved_expression`,
the same conservative classification already applied to top-level programs.
CLI JSON gained a shared `_diagram_summary` helper (extracted rather than
duplicated) so `function_blocks[].body[].diagrams` now carries full
object/pin detail, including `target_parameter`, matching what
`programs[].routines[].diagrams` already exposed. 15 targeted tests passed
(11 direct unit tests covering isolation, cross-FB independence, and the
parameter/local-tag collision case, plus 4 end-to-end); full suite (1249
tests) passed; Ruff and Pyright passed, including a full repo-wide Pyright
re-check since this touched the shared `GraphicalPin` model.

Documented dependency order checkpoint (2026-09-21): multi-block FBD order
now resolves from a real Schneider FAQ (FA340273), already cited in the
schema's `execution_rule_source` but never previously used to resolve
anything. The FAQ's own words: FFBs with no other FFB as input execute
first, top to bottom; FFBs that do have one execute after, also top to
bottom -- dependency overrides position when they conflict (its own example:
"FFB 13 will be executed before the 11 that is above"). That is a two-level
example. Real corpus dependency chains run up to 7 levels deep (28 diagrams
with dependencies, all acyclic) -- deep enough that the literal two-bucket
reading breaks down, since every block past the first level lands in the
same "has input" bucket, ordered only by position. A full topological sort
(Kahn's algorithm, releasing each wave of position-sorted, now-satisfied
blocks) is the mathematically necessary generalization, and collapses to
exactly the documented rule for the 2-level case -- but going from one
documented level to N is still an extrapolation this pass is explicit about,
not a separately vendor-confirmed rule; recorded as
`execution_order_basis = "documented_dependency_order"`, a distinct label
from `"single_block_network"`.

The dependency graph is built only from resolved `linkFB` connections --
never from `shared_variables`, which this project already proved once are
not reliably wires (the withdrawn `shared_variable_dataflow` basis). Any
shared-variable output/input pair *not* also backed by a resolved link
disqualifies the whole diagram from resolution; this is not theoretical --
3 real diagrams in the corpus (`IO_READVAR`, `PC_T_GEN`, `P_MUX3`, all DFB
bodies, out of this pass's scope anyway) have exactly this shape. An
unresolved link, a cycle, or any block missing a grid position also
disqualifies resolution outright (a new `cyclic_block_dependency` diagnostic
covers the cycle case; none occurred in the real corpus).

A real finding changed scope mid-implementation: the pre-existing
unresolved-pin gate (skip the whole diagram if any pin anywhere has an
unresolved symbol) made the new sort resolve zero real diagrams, since every
one of the 22 real FBD networks has at least one such pin somewhere. That
gate predates real resolution and has no bearing on link trustworthiness --
an unrelated pin failing to resolve to a *symbol* says nothing about whether
an explicit block-to-block wire is real. Loosened it for order resolution
specifically, keeping it in front of the separate `ambiguous_block_order`
shared-variable check where it remains relevant. This pass is scoped to
`controller.programs` only, matching the function's existing structure;
DFB-body FBD diagrams (10 real ones) are not yet included -- a natural,
low-risk follow-up, not attempted here to keep this pass's diff reviewable.

All 22 real FBD diagrams (up to 80 blocks each) now resolve; every resolved
order was checked to respect every real link dependency exactly. 22 targeted
tests passed (11 new: two-level and deep-chain resolution, position tie-break,
dependency-overrides-position, cycle detection, unresolved-link and
unlinked-shared-variable disqualification, the loosened-gate regression case,
plus the full real fixture); full suite (1259 tests) passed; Ruff and
Pyright passed, including a full repo-wide Pyright re-check.

DFB-body execution order checkpoint (2026-09-21): the low-risk follow-up
flagged above is done. The per-diagram resolution logic was extracted into a
private `_resolve_routine_diagrams` helper (mirroring the FB-local binding
refactor's shape), called once for `controller.programs` and once for
`controller.add_on_instructions`; `ExecutionOrderIssue` gained `scope: str =
"program"` and the `excluded`/`function_block_excluded` parameters keep the
two scopes' exclusion sets from colliding even if a Program and a DFB
somehow shared a name. All algorithm logic is unchanged -- resolving order
is purely diagram-local (blocks, links, positions), so unlike pin binding
there was never a scoping *semantics* question here, only a scope
*coverage* one.

This gave the unlinked-shared-variable guard (added in the previous
checkpoint, until now only exercised synthetically) its first real test: of
10 real FBD-bodied DFBs, exactly the 3 already identified as having that
shape (`IO_READVAR`, `PC_T_GEN`, `P_MUX3`) correctly stay unresolved; the
other 7 resolve. A real Control Expert engineer's judgment about whether
those 3 diagrams' unlinked shared variables really are wires remains
exactly as necessary as it was -- this pass does not and should not guess.

A second, unplanned finding surfaced while extending the final catch-all
diagnostic loop to also cover DFB routines: doing so required iterating
`diagram.language` for the first time in that loop, which exposed that the
existing code reported `unresolved_block_order` for *every* LD diagram,
unconditionally, forever -- `execution_order_resolved` never becomes `True`
for LD by any mechanism (only FBD is topologically sorted), so this was
pure noise, not information distinct from `diagram.language == "LD"`
itself. Filtered it out for LD; confirmed no existing test relied on the
old noisy count, and added one locking in the corrected behavior. A real,
user-visible diagnostic-count change, called out explicitly rather than
folded silently into the DFB-scope extension.

10 targeted tests passed (real-fixture assertions split by scope, plus the
LD-noise regression case) on top of the previous checkpoint's 22; full
suite (1260 tests) passed; Ruff and Pyright passed, including a full
repo-wide Pyright re-check.

`shortCircuit`/SCE checkpoint (2026-09-22): official Schneider Machine
Expert documentation ("Parallel Branch", product-help.se.com,
EIO0000002854.00) names the Ladder double-vertical-line construct "Short
Circuit Evaluation" -- a conditional bypass for a block with a boolean
input/output. Re-examining the real evidence in detail (hand-computed grid
columns/rows, cross-checked against every real `objPosition`) found that no
fixture in the corpus actually shows that shape; every real `shortCircuit`
instead feeds one target pin directly. Two consecutive AskUserQuestion
course-corrections happened during this work: first, scope was narrowed
from "implement the vendor's bypass semantics" to "resolve only the
structural connectivity the evidence actually supports" once the mismatch
surfaced; second, after finding a genuine multi-row-block pin-mapping
ambiguity (see below), the user chose to keep investigating with the
existing corpus rather than pause for more fixtures, which is what
produced the final, narrower rule. See the architecture doc's new
`shortCircuit`/SCE section for the full column-arithmetic evidence and the
two real shapes (`resetnoe`'s RESET-vs-SET and `MBP_MSTR_7`) that forced
the lookahead-confirmation refinement.

`resolve_ladder_pin_conditions` (`ladder.py`) resolves vertical wires that
land cleanly on a target `FFBBlock`'s `EN` pin -- the only pin ever
evidenced as a target -- and leaves every other shape (dangling, or a
`VLink` still alive one row past a candidate landing) diagnosed by the
existing row-level mechanism, not guessed. Resolved conditions attach to
the matching `GraphicalPin.ladder_condition` (a new field, distinct from
`expression`/`target_tag`, since this comes from grid geometry, not a
source attribute) via a new `LadderPinCondition` model type.

4 real EN conditions resolve identically in `function15.zip` and
`function2.zip` (`.2`/SET, `.4`/ADD, `.5`/ADD, `.4`/SET unconditional);
zero elsewhere in the corpus, including both of the escalator's
`shortCircuit` occurrences (which dangle, reaching no block at all). 6
new targeted tests passed (4 synthetic shapes, 1 malformed-shape
diagnostic, 1 real-fixture assertion covering both zip archives); full
suite (1266 tests) passed; Ruff and Pyright passed, including a full
repo-wide Pyright re-check.

Section condition checkpoint (2026-09-22): the corpus contains real
`activationCondition`/`logicCondition` attributes -- previously unmodelled --
on `sectionDesc` (`Sim_FBD`, `Sim_ST`: `activationCondition="SIM"`,
`logicCondition="standard"`) and on an `FBProgram` (`IO_AI_EX/INIT`:
`activationCondition="%S13"`), all in `estradege_m580-safety.xef`. They are now
recorded in the routine's `task_schedule` entry (`section_conditions`, present
only when declared) and in a Function Block body routine's
`metadata["section_conditions"]`, kept separate from task scheduling; the
existing `execution_conditions: "not_evaluated"` marker is unchanged. The
activation text is classified by shape only: `direct_address` (`%S13`; the
address is not interpreted), `declared_symbol` (exactly one global variable),
`missing_symbol`, `ambiguous_symbol`, `unresolved_expression`, or -- inside a
Function Block body, which has its own namespace -- `function_block_scope_unresolved`.
Anything not `declared_symbol`/`direct_address` raises
`unresolved_section_activation_condition`. The `logicCondition` keyword is
retained verbatim with no meaning assigned. Real finding: `SIM` is declared in
that export only as Function Block input parameters, never as a global
variable, so both section conditions correctly stay `missing_symbol` rather than
binding to a same-named parameter. Also observed and left alone: `IO_AI_EX` has
two `FBProgram` sections (`INIT`, `MAIN`), which existing capture diagnoses as
`ambiguous_function_block_body`, so its `%S13` condition is not reachable yet.
5 new targeted tests passed (synthetic cases plus the real fixture); full suite
(1273 tests) passed; Ruff and Pyright passed.

`execAfter` checkpoint (2026-09-22): a block whose `execAfter` names another
block in the same network (matched case-insensitively by instance name) now
gains a dependency edge onto it, ahead of the position tie-break; the result is
labelled `execution_order_basis = "dependency_order_with_exec_after"` so it is
distinguishable from the FAQ-documented order. Evidence is deliberately
limited: Schneider's FAQ FA332812 confirms a block property can force
execution order but documents neither the mechanism nor the value grammar, so
reading the attribute as "runs after the named block" rests on its name plus a
single real occurrence (`IO_AI_EX`-family `IO_READVAR`, `SR_1` -> `CTU_UINT_1`).
A value naming zero, several or the block itself raises
`unresolved_execution_after` and leaves the order unresolved; an override that
closes a cycle with links raises `cyclic_block_dependency`. That one real
network still does not resolve, for an unrelated pre-existing reason: `BUSY`
feeds four inputs with no covering `linkFB`, which is treated as an incomplete
graph. So the real corpus gains no new resolved network; this is covered by 4
new synthetic tests only. Full suite (1279 tests) passed; Ruff and Pyright
passed.

Multi-section Function Block checkpoint (2026-09-22): a `FBSource` with several
`FBProgram` sections was previously rejected wholesale as
`ambiguous_function_block_body`. Two real blocks have them -- `IO_AI_EX`
(`INIT`, `MAIN`) in `estradege_m580-safety.xef` and `DFBTYPE1` (`code1`, `code2`)
in `estradege_m340.xef` -- so every section is now captured as its own routine,
keyed by section name, with `metadata["function_block_section"]` recording its
document index and the section count. A lone section keeps the block's own name
and no such metadata, unchanged. Sections without distinct names (missing, or
equal ignoring case) still raise `ambiguous_function_block_body` rather than
being guessed at. Section index is provenance only: no execution order or
call-time behaviour between sections (for example when `INIT` runs) is claimed,
since none is evidenced. This also makes `IO_AI_EX/INIT`'s
`activationCondition="%S13"` reachable (`direct_address`). Existing per-routine
analyses (binding, ordering, isolated FB namespace) apply to each section
unchanged. The real-fixture expectations moved accordingly (66 ST bodies, 7
encrypted, 0 ambiguous, previously 65/8/1). 3 new synthetic tests plus the
updated real-fixture assertions; full suite (1282 tests) passed; Ruff and
Pyright passed.

Member path checkpoint (2026-09-22): pin and contact/coil expressions shaped as
index, member or bit-select paths (`T1.STAT.6`, `GEST[1].0`, `OBJ2.OUT1`) were
all `unresolved_expression`. `analysis/member_paths.py` now resolves a path
only when every step is proven: the base is a unique declared symbol; each
`.name` is a unique member of its DDT, of a user Function Block's declared
parameters, or of a library interface's parameters (Function Block local
variables are never reached, since their public/private split is not
captured); each `[n]` is an integer literal within the declared bounds (a
non-zero lower bound is honoured, never zero-based); each `.n` is a bit of a
fixed-width integer type (BYTE/WORD/DWORD/INT/UINT/DINT/UDINT, bit < width --
the form is corpus-evidenced, e.g. `_fault.0`, not vendor-quoted). Resolved
pins get `binding_kind = "declared_member_path"` and a `MemberPath` (declared
spelling of each step, proven final type); `target_tag`/`target_parameter`
name the base symbol only. Such pins deliberately do not join
`shared_variables` groups, so they neither create nor hide dependencies. A
literal index or bit outside the declared range is
`member_path_out_of_bounds` with a `*_member_path_out_of_bounds` diagnostic;
a non-literal index, multi-dimensional array, unknown member or unproven base
stays `unresolved_expression`, unchanged. Real corpus: 30 expressions resolve
(29 in the M580 safety project, 1 in the M340 project), none out of bounds.
That was only 30 of ~420 index/member expressions at the time; see the
resource variable checkpoint below for why and what changed. Full suite
(1304 tests) passed; Ruff and Pyright passed.

Resource variable checkpoint (2026-09-22): the M580 safety project keeps its
variables inside each `resource` (`inputParameters`, `outputParameters`,
`privateLocalVariables`; `process` 731, `safe` 150), never in the top-level
`dataBlock`, which is empty there -- so that project previously had no
captured variables at all. They are now captured into a new `Resource` model
(`Controller.resources`), deliberately not merged into `controller.tags`: the
two resources declare 27 of the same names independently, and analyses that
read `controller.tags` assume one flat scope. Each task records its owning
`resource`. A program binds against the controller's variables plus its own
resource's (resolved through the task that schedules it, and only when every
scheduling task agrees on one resource); a name declared in both scopes, or
twice inside one resource, is `ambiguous_symbol`, never picked. Real result:
881 resource variables captured, none ambiguous; program-scope pins that were
unbound now bind, and resolved member paths rose from 30 to 98. Two honest
consequences: (1) 8 of 22 program FBD networks (`Sim_FBD`, `Sim_W505`,
`MAV10EA100`, `MAK10EA100`, `MAX10EA100`, `MAL10EA100`, `MKA10EA100`,
`TRIP_TG`) no longer report a resolved execution order. Their pins used to be
unbound, which blinded the unlinked-shared-variable guard; now that the
variables bind, blocks are seen exchanging values through a shared variable
with no covering `linkFB`, which that guard treats as an incomplete graph. The
earlier 22/22 was therefore over-claimed. (2) ~320 expressions such as
`AIS_00MAA10CP004.CH_HEALTH` still cannot resolve: their bases are typed by
library device types (`T_U_DIS_STD_CH_IN`, `T_U_ANA_STD_CH_IN`, ...) that the
export does not define, so no member is provable. That needs the library
DDT definitions as evidence; it is not a parser gap. Not extended: SFC
expression binding and other analyses still see only controller-level
variables. Also outstanding: ~480 expressions that are not member paths at
all (direct addresses like `%S6`, time literals, digit-leading names such as
`00BBA01GS001.CLOSED`). 3 new synthetic tests plus 1 real-fixture test; full
suite (1307 tests) passed; Ruff and Pyright passed.

Digit-led name checkpoint (2026-09-22): real names in this corpus are
KKS-coded plant tags (the power-plant equipment identification standard),
which may start with digits (`00BBA01GS001`, a circuit breaker; `.CLOSED` is
its member) -- confirmed real by a user, not previously evidenced as a naming
convention here. The identifier grammar required a leading letter/underscore,
so every such name failed before member-path resolution ever ran. It now also
accepts one or more leading digits followed by at least one letter/underscore
(`ExpressionSpec.identifier`), applied everywhere it is used: pin/contact/coil
binding, member paths, SFC two-part bindings, and section activation
conditions. A token that is purely digits still cannot match -- required, so a
bit-select index (`.6`) and a numeric literal (`123`) both stay unambiguous
from a name. This is a single shared grammar change, not a new mechanism, so
no new diagnostic codes. Real result: resolved member paths in the M580 safety
project rose from 98 to 375 (unresolved pin expressions dropped from 804 to
506); no new out-of-bounds results; execution order results unchanged from the
prior checkpoint (same 8 program networks and 3 DFB bodies stay unresolved for
the unlinked-shared-variable reason already recorded there). 8 new tests
(synthetic digit-led/pure-digit cases plus a real-fixture assertion on
`00BBA01GS001.CLOSED`); full suite (1313 tests) passed; Ruff and Pyright
passed.

Device DDT catalog checkpoint (2026-09-22): the ~320 remaining unresolved
member paths after the resource variable checkpoint all had bases typed by
standard Universal I/O "Device DDT" types (`T_U_DIS_STD_CH_IN`,
`T_U_ANA_STD_CH_IN`, ...) -- real, vendor-predefined structures that Control
Expert auto-generates from a configured module's DTM, confirmed real by a
user's domain knowledge of a related name (`00BBA01GS001`, a KKS-coded
circuit breaker tag) prompting this investigation. This export never
serializes their structure (unlike `T_BMENOC0321`/`T_BMEP58_ECPU_EXT`, which
are genuinely configured head-end modules and do get a real `DDTSource`) --
confirmed by checking the whole file for any other definition of these names,
finding none. The real module catalog numbers are present, though
(`BMXDDI3202K`, `BMXAMI0800`, `BMXSAI0410`, ...), which identified the exact
public Schneider manuals to check. `schema/control_expert/device_ddt_catalog.py`
now transcribes the documented structure of the 8 types this export actually
uses, each member name and type taken verbatim from a cited manual page (not
inferred from how the project happens to use a field) -- discrete and analog
standard channels from the Modicon X80 I/O user manuals (35012474, 35011978),
safety channels from the Modicon M580 Safety Manual (QGH46982.08). A table
column that PDF extraction rendered ambiguously (e.g. some bit-level fields in
the analog standard channel table) was left out rather than guessed at. The
catalog only supplements `MemberPathContext.datatypes` inside member-path
resolution -- never merged into a parsed project's own `Controller.datatypes`,
so nothing is ever reported as if this project had captured it; a project's
own real `DDTSource` of the same name (not expected, but not assumed
impossible) still wins. Real result: resolved member paths in the M580 safety
project rose from 375 to 688 (98 unique to 471 unique expressions); unresolved
pin expressions dropped from 506 to 193; no out-of-bounds results; execution
order unchanged from the prior checkpoint. What's left in the remaining 193 is
a genuinely different mix -- binary literals with a `_` digit separator our
literal grammar doesn't cover, full comparison/function-call expressions,
non-ASCII names, and a few bases that are missing or ambiguous -- correctly
untouched by this change. 14 new tests (per-type resolution, catalog/project
precedence, non-leakage into `Controller.datatypes`, a real-fixture check);
full suite (1327 tests) passed; Ruff and Pyright passed.

Literal grammar checkpoint (2026-09-22): two IEC 61131-3 standard literal
forms were unevidenced gaps in `ExpressionSpec.literals`, found while
surveying what remained unresolved after the Device DDT catalog checkpoint --
not vendor-specific, so added directly rather than treated as a vendor rule
needing its own citation. (1) A TIME literal (`t#200ms`, `T#24h`, `t#0.5s`,
optionally signed) is now a literal; scope is deliberately bounded to the
single-unit shapes this corpus evidences (36 distinct real ones) -- no
combined multi-unit form like `t#1d2h` is evidenced, so that stays
unresolved. (2) A `"_"` digit separator between digits is now accepted in
binary/octal/hex literals (`16#0000_0001`, `2#111_1000_0000`), matching real
and common corpus usage; a leading, trailing or doubled separator still fails
to match, on purpose. Plain integer/real literals are deliberately not
extended the same way -- no corpus evidence of an underscore in either form
was found. Real result: recognized literals in the M580 safety project rose
from 633 to 709 (exactly the 39 TIME + 37 based-literal instances evidenced);
unresolved pin expressions dropped from 193 to 117. 2 new tests (positive
shapes including the sign/case variants, and a negative set covering
malformed separators and the unevidenced combined TIME form); full suite
(1328 tests) passed; Ruff and Pyright passed.

Accented identifier checkpoint (2026-09-22): real declared tags in this
corpus use French accented letters -- "�" (e.g. `TG_R�seau`) and "�"
(`Vit_STOP_Soul�vmt`) -- confirmed by checking every declared name across the
whole corpus (controller/resource/program tags, DDT members, Function Block
parameters and locals): exactly these two letters, both cases, never as a
name's first character. `ExpressionSpec.identifier` now accepts them in the
continuation position only, mirroring the digit-led KKS fix's shape and
scope -- not a general Unicode-identifier allowance, since nothing else is
evidenced. Real result: in the M580 safety project, 22 more pins bind to a
declared symbol and 1 more resolves a member path (`Vit_STOP_Soul�vmt.IND`);
unresolved pin expressions dropped from 117 to 94. 3 new tests (both letters,
plus a full-pipeline case-insensitive lookup with an uppercase accent). Full
suite (1331 tests) passed; Ruff and Pyright passed.

Public local member-path checkpoint (2026-09-22): real graphical pins in the
M580 safety project reference a Function Block instance's own local variable
from *outside* the instance -- e.g. `PM5320.ACPT`, an output pin's
`effectiveParameter`, where `ACPT` is declared in `IO_PM5320`'s own
`<publicLocalVariables>`, not its parameter interface. Public vs private is a
real, separate Control Expert XML distinction (two different elements) that
capture previously discarded, merging both into one `local_tags` dict with no
visibility record -- not because the distinction was unproven, but because
nothing had yet used it. Each local `Tag` now carries
`metadata["visibility"] = "public"` or `"private"`. Member-path resolution's
external view of a Function Block instance (`member_path_context`) now
includes a public local alongside its declared parameters; a private local is
still never proven reachable from outside, on purpose. This is deliberately
narrow: it does not touch binding *inside* the FB's own body (already
correctly sees every local, public or private, per the isolated-namespace
checkpoint), and it does not extend the SFC two-part binding in
`sequential_bindings.py`, which has its own, separate FB-member lookup not
touched here. Real result: resolved member paths in the M580 safety project
rose from 689 to 715; unresolved pin expressions dropped from 94 to 68. 4 new
tests (context construction, a real external-reference shape resolving while
a private local on the same instance does not, and confirmation that
in-body binding is unaffected); full suite (1334 tests) passed; Ruff and
Pyright passed.

Tier 1 binary expression checkpoint (2026-09-22): after every prior member
path checkpoint, 68 unresolved pin/contact/coil expressions in the M580
safety project remained. Surveyed by shape: comparison (`Mode=8`,
`StepNo>=4`), arithmetic (`PV1/9000.0`, `TR_H -0.5`), logical `and`/`or`
mixed with comparison (`Reset or GQC=65535` -- needs real IEC 61131-3
precedence, comparisons binding tighter than AND, tighter than OR), and
inline function/EF calls (`RE(Sim_W505_STOP)`, `ADDMX (IN := '...')` -- a
call-site parameter-binding problem, not an operator grammar at all). Given
the user's explicit choice of scope, only the first two shapes (Tier 1) are
resolved now; the rest stay unresolved on purpose, not a gap.
`analysis/simple_expressions.py` recognizes exactly one occurrence of a
comparison or arithmetic operator (`=`, `<>`, `<`, `>`, `<=`, `>=`, `+`, `-`,
`*`, `/`) splitting an expression into two operands, each independently
classified the same way a standalone expression already is (literal,
declared symbol, or proven member path); both must resolve or the whole
expression stays `unresolved_expression`, unchanged. A leading sign (e.g.
`-3`) is never split, since such a token is already consumed as a signed
literal before this stage runs; an expression containing a string literal is
never split, to guard against an operator character appearing inside quoted
text; `:=` is explicitly never read as `=` (guards the excluded call-site
case from a spurious partial split). A resolved binary expression gets
`binding_kind`/`operand_binding_kind = "declared_expression"` and a new
`BinaryExpression` (operator plus two `ExpressionOperand`s); it is
deliberately never added to `shared_variables`, matching every other
non-plain-symbol resolution. This computes no truth value, arithmetic result,
or type compatibility -- structural evidence only, exactly like a MemberPath.
Real result: 52 pin/operand occurrences (43 distinct expressions) now resolve;
unresolved pin expressions dropped from 68 to 16. One side effect, the same
shape as the resource-variable checkpoint's: a 9th program FBD network
(`S�quence`) and the DFB body pins whose blocks feed a shared variable with no
covering `linkFB` newly become visible to the unlinked-shared-variable guard
once their pins bind, so it correctly stops claiming an order for that
network too -- an existing test's expectations moved accordingly. 8 new tests
(split-shape coverage including the `:=`/quote/multi-operator guards, operand
classification, a real-fixture check); full suite (1364 tests) passed; Ruff
and Pyright passed.

Tier 2 binary expression checkpoint (2026-09-22): after Tier 1, 3 real
expressions remained that need a logical AND/OR: `GEST[2] and 16#0F`,
`Reset or GQC=65535`, `Reset or BQC=65535`. `split_logical_expression` now
recognizes exactly one occurrence of AND or OR (checked in that
precedence order -- OR is outermost, matching real IEC 61131-3 precedence,
not an invented rule), word-bounded so it never matches inside a longer
identifier (`Corridor`, `Sandbox`). Each side resolves either as a plain
operand or, matching the real evidenced shape, as its own Tier 1
comparison/arithmetic expression (`GQC=65535`) -- never as a further logical
expression, since real precedence puts comparison inside AND inside OR, not
the reverse. This is implemented as genuine (if shallow) recursion rather
than a hardcoded two-level special case, but stays exactly as conservative at
every level: more than one occurrence of the same keyword (`A and B and C`)
is refused, matching Tier 1's refusal of a second occurrence of the same
comparison/arithmetic operator, since left-associative chaining of either is
unevidenced. `ExpressionOperand` gained `sub_expression` for this one
evidenced case (a logical operand that is itself a comparison), not a
general nested-expression allowance. Real result: all 3 resolve; unresolved
pin/operand expressions dropped from 16 to 13. What remains in those 13 is
exactly the two categories the Tier 1 checkpoint already named as
out-of-scope (3 function/EF calls) plus symbols this export never defines (4
uses of `Para_PI`/`Mode_MH`, plus one `%S6` direct address) -- not a grammar
gap. 8 new tests (split-precedence coverage including the substring-boundary
guard, nested-comparison resolution, real-fixture check); full suite
(1378 tests) passed; Ruff and Pyright passed.

Direct address classification checkpoint (2026-09-22): a "%..." direct/system
address (e.g. `%S1`, `%S6`) used as a pin or contact/coil expression fell into
`unresolved_expression`, even though this project already recognizes the
exact same shape elsewhere (`ExpressionSpec.direct_address`, used for section
activation conditions). Pins and contact/coil operands now classify it too,
as `binding_kind`/`operand_binding_kind = "direct_address"` -- evidence, not
a resolved target: no `Tag`/parameter/member path is attached, the same way
a `"literal"` classification carries no target. Kept strictly opt-in
(`direct_address_pattern: str | None = None`, only classified when a caller
passes it): `resolve_graphical_bindings`/`resolve_function_block_bindings`
callers that do not ask for it keep the prior behavior unchanged. Real result
across the whole corpus (not only the M580 safety project): 6 occurrences
(`%S1` x4 on contact/coil operands, `%S6` x2 on pins), all newly classified;
no diagnostic is raised for them, matching `"literal"`. 3 new tests
(pin/output-pin classification, the opt-in default, a real-fixture check);
full suite (1381 tests) passed; Ruff and Pyright passed.

This closes out the corpus-evidenced work in `docs/roadmaps/control-expert-roadmap.md`
originating from the indexed/member-expression and control-flow investigation
threads. What remains unresolved in the M580 safety project (10 expressions)
is, by shape: 3 inline function/EF calls (`RE(...)`, `ADDMX(...)`,
`UDINT_TO_TIME(...)`) -- a call-site parameter-binding problem, not an
operator grammar, and a materially different task; and 4 uses of `Para_PI`/
`Mode_MH`, types this export never defines and no public manual has been
found for (unlike the Device DDT catalog's types) -- blocked on evidence, not
effort.

`jumpSFC` checkpoint (2026-09-22): `apexsotjo-blip/control-expert-mcp` (a real
MCP server that drives a licensed Control Expert 14.0 installation via its own
COM automation, not a black-box reverse-engineering exercise) ships
`tools/lang_refs/SFC_0_Packaging_Robot.xml` -- not synthetic content: its
`contentHeader` credits a real, dated, independently authored demo project
("injection molding machine", Stefan Probst, 07.05.2003; the same repo's
other `lang_refs/` files are further sections of the identical demo).
Copied into `reference/control-expert/probst_injection_molding_sfc_packaging_robot.xml`.
It is a bare section export (`SFCExchangeFile`), not a whole project
(`ZEFExchangeFile`/`FEFExchangeFile`); its real `<SFCProgram>`/`<dataBlock>`
content is wrapped in a minimal project envelope for testing -- the same
technique this test file's own `_chart()` helper already uses for synthetic
content, applied here to real content instead.

`jumpSFC stepName="..."` is now captured (`step_jump` kind,
`properties["step_name"]` the raw reference) and resolves in
`sfc_connectivity.py` exactly like `alternative_join`: a transition whose
grid-adjacent successor is a `jumpSFC` resolves onward, directly to the step
it uniquely names -- `named_jump_indirection` basis, distinct from
`grid_adjacency`/`explicit_link`/`join_indirection`. Scope is deliberately
narrow: only within the same network, matching both real evidenced usages
("close the loop" back to a step in their own network); a missing, ambiguous,
or cross-network target stays `unresolved_sfc_successor`, and a `jumpSFC`
competing with a plain adjacent step or an explicit link at the same position
is `ambiguous_sfc_successor` -- the same three-way conflict rule already
governing plain adjacency vs. explicit links. No new capture diagnostic code
was needed; both existing `unresolved_sfc_successor`/`ambiguous_sfc_successor`
codes already fit.

Real result: the fixture's one `jumpSFC` (`Start_Robot`) resolves correctly,
confirmed by locating both the jump element and its target step
independently and asserting the edge connects them. The chart does *not*
fully resolve end to end, for an unrelated, pre-existing reason: its
`altBranch width="4"` has transitions at only 2 of its 4 declared columns (a
sparser real layout than the Annecy fixture the branch-column rule was built
from), correctly left `unsupported_sfc_branch_position` rather than guessed
at -- not a regression from this work, and not silently hidden by the test.
4 new synthetic tests (closing-loop resolution, missing/ambiguous target,
competing-candidate ambiguity) plus the real-fixture test; full suite
(1385 tests) passed; Ruff and Pyright passed.
