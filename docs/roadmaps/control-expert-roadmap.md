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
- [ ] Backlog: `parBranch`/`parJoint` (simultaneous/AND branching) and `jumpSFC` (named
      jump to a step) grammar. Currently documented only by a third party's own
      reverse-engineering (`apexsotjo-blip/control-expert-mcp`'s `lang_reference.py`
      and `tools/lang_refs/`), not by any captured export in the corpus. Do not
      implement from that description alone; wait for a real fixture, the same
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
- [ ] Resolve multi-block FBD order from verified vendor rules; shared variables alone are insufficient
- [x] Resolve simple declared-variable pin expressions case-insensitively
- [x] Classify supported lexical literals, unbound pins and unresolved expressions
- [x] Group shared-variable references without inventing graphical wires
- [x] Preserve ambiguous declarations instead of binding to the first occurrence
- [x] Capture and validate library block interfaces against actual calls
- [x] Resolve LD contact step-state member expressions against declared SFC steps
- [ ] Resolve indexed and other member expressions using proven type definitions and bounds
- [ ] Interpret explicit FBD links/connectors with endpoint diagnostics
- [x] Decode Ladder grid connectivity for the pure-series case (contacts in
      series to one trailing coil, per row); see the Ladder series checkpoint
      below for scope
- [ ] Backlog: Ladder `shortCircuit`/`VLink` branch and vertical-wire routing,
      and `FFBBlock` pin wiring within a Ladder network (EN/IN/etc.). Real
      corpus evidence (`function15.zip`) shows a single vertical wire can span
      many rows to reach a distant block, not just an adjacent-row OR-merge --
      the exact rule is not yet evidenced well enough to resolve, so every row
      touching these stays diagnosed (`unresolved_ladder_row`), never guessed.
- [ ] Resolve multi-block/network order under documented link and override rules
  (dataflow-only ordering above does not yet cover explicit links or `execAfter`)
- [ ] Interpret section conditions, enable behavior, jumps and other control flow
- [ ] Produce executable neutral graph/IR only for a verified semantic subset

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

## Milestone 5: broader type and source coverage — pending

- [ ] Promote a documented subset of scalar initial values with lexical provenance
- [ ] Model array lower bounds and composite initialization without zero-base loss
- [ ] Capture DDT, device DDT and custom DFB definitions and references
- [ ] Distinguish library types, block-instance types and user-defined data types
- [ ] Extend ST analysis with source dialect/system-address evidence
- [ ] Add SFC, IL/LL984 and additional task/hardware forms as evidence becomes available
- [ ] Add populated DTM and modern M580/Control Expert examples
- [ ] Characterize encrypted/protected exports and retain unsupported content

No inferred DTDVersion-to-release table: preserve the marker alongside exporter
identity and actual feature coverage.

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
uv run pytest tests/test_control_expert_sfc.py tests/test_control_expert_capture.py tests/test_control_expert_project.py tests/test_control_expert_graphical.py tests/test_graphical_bindings.py tests/test_cli_control_expert.py tests/test_model_json_export.py tests/test_sfc_connectivity.py tests/test_sfc_coverage.py tests/test_control_expert_ladder.py
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
