# Control Expert import: development checkpoint journal

This is the dated history of implementation checkpoints for the Control
Expert/Unity Pro XEF/ZEF import work: what was measured, what real corpus
evidence justified each change, and exact test/lint/type-check results at
the time. It is a development log, not a plan.

- Delivery status and what's next: the
  [Control Expert roadmap](../roadmaps/control-expert-roadmap.md).
- Observed structures, mapping decisions and evidence references: the
  [capture and mapping specification](../architecture/control-expert-exchange-capture.md).

Entries are in chronological order (oldest first) and are never rewritten
after the fact; a later entry may supersede or withdraw an earlier one, but
the earlier entry stays as the historical record.

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

Scalar initial value checkpoint (2026-09-23): a top-level tag's
`<variableInit value="...">` was retained only as lexical
`metadata["source_initial_values"]`, with `Tag.initial_value` -- a field this
project's model already defines, used by the L5X converter -- never
populated for Control Expert. `_promote_initial_value()` now promotes it to a
`TagValue` when the literal text matches a shape this project already
recognizes elsewhere (`EXPRESSION_SPEC.literals`) *and* the declared type is
one real initializers here actually use: BOOL/EBOOL (`TRUE`/`FALSE`, and
`"0"`/`"1"` -- standard IEC 61131-3 BOOL literal syntax, real evidence:
`Sim_BBA01_PFe="0"`, `Sim_BBB01_PFe="1"`), an integer family (plain or based
literal, reusing this project's own digit-separator support), or REAL/LREAL.
TIME (6 real occurrences, `t#10s`/`t#20s`) stays lexical-only on purpose --
no duration-to-integer conversion factor is invented, the same restraint the
L5X converter's own scalar promotion (`converters/l5x/decorated_value.py`)
already applies to types it does not recognize. More than one initializer on
one tag (never evidenced, always exactly one in this corpus) is never
guessed at either. `uninterpreted_initial_value` now fires only when nothing
promoted, not unconditionally as before. Composite (struct/array)
initialization and DDT *member* initializers (a separate, pre-existing gap:
member initializers are not captured at all yet, lexically or otherwise) stay
out of scope, as already noted elsewhere for the former. Real result: 21 of
27 real tag initializers promote (15 REAL, 4 BOOL, 2 INT); the 6 TIME ones
correctly stay unpromoted. 14 new tests (one per promotable shape, malformed/
unsupported/multi-initializer cases, a real-fixture check); full suite
(1404 tests) passed; Ruff and Pyright passed.

Encrypted body checkpoint (2026-09-23): a crypted Function Block's opaque hex
body (`<crypted Encoding="65001">...</crypted>`) was detected (the existing
`encrypted_function_block_body` diagnostic) but never exposed on the neutral
model -- only the interface was retained there, even though the full blob
was already preserved verbatim at the capture layer (`source_extensions`),
as it is for every other element. "Characterize" is read narrowly: describe
the opaque content (its size, its declared encoding, and a hash for identity/
change-detection across exports), not embed the full blob into
`AddOnInstruction.metadata["encrypted_body"]` -- real blobs range from 2.3 KB
to 68 KB of hex per block, disproportionate to duplicate into every
inspection report when the source is already retained losslessly elsewhere.
`AddOnInstruction` gained a `metadata` dict (a field every other named model
type already has; this one did not). 2 of the M580 safety project's 7
crypted blocks have no `Encoding` attribute at all (still real, still
hex-bodied) -- both shapes are captured. Real result: all 7 blocks now carry
`{"encoding": "65001"|None, "hex_length": <2300..67750>, "sha256": <hex>}`.
2 new tests (with/without the `Encoding` attribute) plus updated real-fixture
assertions; full suite (1405 tests) passed; Ruff and Pyright passed.

Type distinction checkpoint (2026-09-23): a tag typed as a captured
Function Block (DFB) instance or a library (EFB) block type -- `TON`,
`S_SR`, `MBP_MSTR`, a user `FBSource`, ... -- was reported `unresolved_type`
exactly like a genuinely undefined type, because only `Controller.datatypes`
(DDTs) was ever checked. `Tag` gained two new fields, `function_block_instance`
(`AddOnInstruction | None`) and `library_type` (`LibraryInterface | None`),
set instead of `data_type_definition` -- a tag's type is exactly one of
these three kinds, never more than one. `_function_blocks` now runs before
`_variables`/`_resources` (it does not itself depend on tags/resources
existing yet) so a DFB instance can be cross-referenced the same as a DDT.
Every DFB is also registered in `library_interfaces` (kind
`"user_function_block"`, for call validation), so a same-named match there
is checked only after the richer `AddOnInstruction` match fails, never
instead of it. Matching is case-insensitive, like everywhere else in this
project. Real result: `unresolved_type` diagnostics dropped from 794 to 327
(336 tags newly resolve to a Function Block instance, 131 to a library
type); the pre-existing 3 DDT-linked tags are unaffected. What remains
`unresolved_type` is genuinely so: mostly the Device DDT catalog's own
types (`T_U_DIS_STD_CH_IN` and siblings -- deliberately not linked here,
since `Tag.data_type_definition`/`function_block_instance`/`library_type`
are read elsewhere as "this project captured this type", and the catalog is
vendor documentation, not project evidence) and multi-dimensional
`ARRAY[...]` types (a separate, already-tracked gap). 6 new tests (each
kind, the DFB/library-interface precedence rule, case-insensitivity, the
negative case, a real-fixture check with exact counts); full suite
(1411 tests) passed; Ruff and Pyright passed.

Device DDT type distinction checkpoint (2026-09-23): the type distinction
checkpoint above deliberately left the Device DDT catalog unlinked from
`Tag.data_type_definition`/`function_block_instance`/`library_type`, all
read elsewhere as "this project captured this type". Revisited here with a
fourth, clearly separate field instead of reversing that: `Tag` gained
`vendor_documented_type` (`Datatype | None`), set only from the catalog,
checked last (after every kind of project evidence). `_type_definition`
returns a 4-tuple now; `device_ddt_catalog.datatypes()` (moved out of
`graphical_bindings.py`, which now calls the same shared function, so the
member-path resolver and tag typing are never out of sync) is built once per
project and shared across every tag, so two tags of the same catalog type
share one `Datatype` instance rather than each getting its own copy.

This also **doubled the catalog**: measuring what remained `unresolved_type`
after the first checkpoint surfaced 11 real *module*-level Device DDTs (a
tag itself typed `T_U_DIS_STD_IN_32`, not just a member path into one) the
channel-level catalog did not cover -- `T_U_DIS_STD_IN_32/64`,
`T_U_DIS_STD_OUT_32/64`, `T_U_ANA_STD_IN_8`, `T_U_ANA_STD_OUT_8`,
`T_U_ANA_TEMP_IN_8` (same X80 manuals as before) and `T_U_ANA_SIS_IN_4`,
`T_U_DIS_SIS_IN_16`, `T_U_DIS_SIS_OUT_4` (M580 Safety Manual, QGH46982.08,
p.56-57/84-86/113-116 respectively -- exact page numbers reverified against
the extracted text, not assumed from the channel-level citations nearby).
Only the exact sizes real tags in this corpus actually use are added, not
every theoretical size the manuals also name. Each module type's simple
status bits (`MOD_HEALTH`, `MOD_FLT`, and for SIS types `SAFE_COM_STS`/
`PP_STS`/`CONF_LOCKED`/`APPLI`/`TIME_PERIOD`/`S_TO`) and channel array(s)
are transcribed; a nested debug sub-structure (`T_SAFE_COM_DBG_IN`/`_OUT`,
itself documented) and `MUID`/`RESERVED` fields are real too but left out --
no real expression in this corpus reaches into them, so their citations
were not chased.

Real result: `unresolved_type` diagnostics dropped further, from 327 to 26
(301 tags now resolve via the catalog). What remains `unresolved_type` is a
different, still-open family entirely: a PID/regulation library
(`Para_PI`/`Mode_MH`/`Para_RAMP`, 11 occurrences), RIO-drop/communication
Device DDTs (`T_M_CRA_EXT_IN` and 3 siblings, 8 occurrences), `ADDR_TYPE`
(2, likely a comms EFB's address structure), `T_U_CRP_STD_IN` (1), and
`WordArr5` (4, likely a generic Schneider array typedef used internally by
communication EFBs) -- none found in any manual searched so far, none
guessed at. 3 new tests (catalog resolution, shared-instance identity across
tags, project-evidence-wins-on-collision) plus updated real-fixture
assertions; full suite (1414 tests) passed; Ruff and Pyright passed.

Composite initial value checkpoint (2026-09-23): `instanceElementDesc` --
Control Expert's generic element for a struct member's, a DFB instance
parameter's, or an array element's initial value, nested arbitrarily deep --
was not captured at all, not even lexically, unlike a scalar tag's own
`<variableInit>`. Real evidence is substantial and was previously
unmeasured: 3684 occurrences in the M580 safety project alone, 142 in the
M340 project, plus more in two zip fixtures. `_composite_value_node()` now
walks the tree recursively into `Tag.composite_initial_value`
(`CompositeTagValue`/`CompositeTagValueNode` -- fields this project's model
already defined, used by the L5X converter, never populated for Control
Expert), distinguishing an array index (`name="[N]"`, real shape, routed to
the node's `index` field) from a named struct/parameter member (routed to
`name`) by lexical shape alone. Deliberately scoped to lexical capture only,
by explicit choice over a larger one-shot version that would also promote
leaf values and resolve member names against DDT members or FB parameters:
`value`/`member_definition`/`data_type_definition` stay `None` on every
node, matching how scalar `initial_value` promotion was itself a separate,
later step after lexical retention. `uninterpreted_composite_initial_value`
is reported for every tag captured this way, mirroring
`uninterpreted_initial_value`. A real, previously unencountered literal
shape surfaced in passing but was not chased further, since promotion is
out of scope here: `tod#00:00:00` (TIME_OF_DAY), not yet in
`ExpressionSpec.literals`. Real result: 214 tags across the corpus now
carry a composite initial value (197 in the M580 safety project alone),
correctly including both DDT-typed struct members and DFB-instance
parameter overrides on the same tag. 3 new tests (nested struct+array
capture matching the real M340 shape, the never-promotes-or-resolves
guard, a real-fixture count) plus an updated existing test; full suite
(1417 tests) passed; Ruff and Pyright passed.

Sequential binding checkpoint (2026-09-23): `resolve_sequential_bindings`
(SFC condition/action `<variableName>` two-part `Tag.Member` binding, e.g.
`Tempo1.Q`) did its own independent lookup -- filtering `library_interfaces`
by `kind == "function_block"` and matching the tag's raw `data_type` string
-- duplicating, and drifting from, the canonical type-resolution mechanism
`Tag.function_block_instance`/`Tag.library_type` already established (see
the type distinction checkpoint above). It now consults those fields
directly instead, gaining the same DFB-instance-wins-over-library-duplicate
precedence for free rather than needing a second, independently-evidenced
implementation. Confirmed by measurement, not assumed: every real
timer-member expression in this corpus already resolves cleanly today (zero
`sfc_*` diagnostics across the whole corpus, all 12 real `Tempo1..6.Q`
references bind), so this is a consistency fix, not a new capability filling
an observed gap.

The refactor surfaced a real, latent gap it does not depend on any real
fixture to justify fixing: `_type_definition`'s library-interface lookup
(and `member_path_context`'s equivalent dict) picked the *first* matching
`LibraryInterface` by name, unlike DDTs and DFB instances, which are
name-unique by construction (`_unique_name` at declaration time) --
nothing enforces that for `EFBSource`/`EFSource`/`FBSource` registrations.
The existing `test_members_require_unique_library_interface` fixture
(two same-named `EFBSource` declarations) caught this immediately once
`resolve_sequential_bindings` started relying on `Tag.library_type`: it
regressed from `unresolved_member` to silently binding to whichever
registration happened first. Both call sites now require a name to be
unique before treating it as resolved -- `_type_definition` returns no
`library_type` at all on a collision (falls through to `unresolved_type`,
matching the existing "ambiguous is never guessed" standard applied
everywhere else in this project), and `member_path_context`'s
`_unique_by_name` drops the key entirely rather than keeping one. No real
corpus project declares the same library interface name twice, so this is a
safety-net fix, not an observed real-corpus regression fix, confirmed by
re-measuring: `unresolved_type`, `fb_instance`, `library_type`, `catalog`
and `ddt` counts are unchanged. 4 new tests (the two ambiguity guards, at
the tag-typing and member-path-context layers respectively); full suite
(1419 tests) passed; Ruff and Pyright passed.

Task timing checkpoint (2026-09-23): a task's `valueType` (periodic rate) and
`maxExecTime` (watchdog) were retained only as lexical
`metadata["source_task_attributes"]`, with `Task.rate`/`Task.watchdog` --
fields this project's model already defines, unused by any converter so
far -- left unset ("Do not assign rate/watchdog units from undocumented raw
values", the exact prior caution this revisits with better evidence than was
available when written). Units are inferred, not from a published XEF schema
for these exact attribute names: `apexsotjo-blip/control-expert-mcp`'s
`bridge.py` reads the same underlying task settings through Control Expert's
own live COM automation (`task.Periodicity`, `task.WatchDog`), and its own
parameters for them are literally named `periodicity_ms`/`watchdog_ms` --
real, if second-hand, confirmation of milliseconds. `maxExecTime` promotes
for every task type; `valueType` only for a `periodic` task, since a cyclic
task's own `valueType="0"` (real, always this value in the corpus) is not a
period at all -- cyclic tasks have no periodic rate concept. Real result: all
18 tasks across the corpus promote cleanly (`watchdog` always set;
`rate` set for the 6 periodic tasks -- values 5 and 20 -- and correctly
`None` for the 12 cyclic ones). 6 new tests (each real shape, missing/
non-numeric attributes, a real-fixture count); full suite (1425 tests)
passed; Ruff and Pyright passed.

Chart control reference checkpoint (2026-09-23): graphical calls to
`INITCHART`/`FREEZECHART`/`SETSTEP` (real `EFSource` library interfaces in
`MultiGrafcet_Coordination_V1_2026.XEF`, whose declared parameters --
`CHARTREF`, `STEPNAME` -- carry Control Expert's own
`SFCCHART_STATE`/`SFCSTEP_STATE` parameter types) previously resolved as
`missing_symbol`: pin resolution only ever tried "is this an in-scope tag",
and a chart or step name is neither -- it identifies an SFC diagram or one
of its steps by name, not a variable. 3 real call sites in that fixture
(`.1 INITCHART CHARTREF="G1"`, `.2 INITCHART CHARTREF="G2"`,
`.3 SETSTEP STEPNAME="G1_0"`) were misclassified this way before the fix.
The mechanism is generalized by declared parameter type rather than by
block name, so it covers any current or future block with an
`SFCCHART_STATE`/`SFCSTEP_STATE`-typed parameter, not just these three: a
new `_call_reference_kind` helper looks up the pin's declared parameter type
from the block's library interface, and pins of that kind are matched
against known program/chart names or, for FBD/LD diagrams outside a chart's
own body, step names -- landing on new `GraphicalPin.target_program_name`/
`target_step_name` fields and `declared_program_reference`/
`declared_step_reference` binding kinds (both proving only that the name is
reachable, never an execution-order or timing claim, matching this
project's existing binding-kind discipline). A same-named tag still takes
precedence over a chart/step interpretation, and a name colliding across
multiple programs or steps still lands on `ambiguous_symbol` rather than
picking one, consistent with the "ambiguous is never guessed" standard
applied everywhere else in this project. Real result: all 3 real call sites
now resolve (`declared_program_reference` x2, `declared_step_reference`
x1) instead of `missing_symbol`. This addresses only the "chart-control
calls" half of the roadmap line above; "multiple writers" -- more than one
call site setting the same chart/step's state -- is a distinct concern this
change does not model (chart/step state has no binding-kind equivalent of
the existing shared-variable multiple-writer guard) and remains open.

A call's chart/step reference resolves inside a Function Block body too
(`resolve_function_block_bindings`), unlike the LD `<step>.X` contact
convention, which stays deliberately FB-scope-empty (a DFB body should not
hardcode a reference to a specific project's own chart). Both share the
same `_resolve_diagrams` core, so this needed its own dedicated
`call_step_names`/`ambiguous_call_step_names` parameter pair, distinct from
`steps`/`step_ambiguous`: it defaults to falling back to `steps` (so
program-scope callers, which already want the same full project-wide
namespace for both purposes, need no changes), but lets
`resolve_function_block_bindings` supply the real project-wide step table
for call resolution while still passing an empty `steps={}` for contact
resolution -- proven by two new tests, one confirming a `SETSTEP` call
inside a DFB body now resolves, one confirming a `.X` contact inside the
same body still does not.

7 new tests (a program reference, a step reference, an undeclared-type call
staying `missing_symbol`, a name-collision case staying `ambiguous_symbol`,
a same-named-tag-wins case, the FB-body call/contact scope-separation pair
above, and a real-fixture check gated on the
`MultiGrafcet_Coordination_V1_2026.XEF` fixture); full suite (1432 tests)
passed; Ruff and Pyright passed.

Library description checkpoint (2026-09-23): `EFSource`/`EFBSource`/
`FBSource` library registrations carry a `TypeDescriptiveForm` attribute --
Schneider's own first-party prose documentation for the block, e.g. "The
function block is used as the On delay. When the function block is called
for the first time, the initial state of ET is "0"." This text was never
actually lost -- `LibraryInterface.source_extensions` already snapshots the
whole registration node losslessly -- but it sat unpromoted alongside
sibling `attribute` pairs this project still does not interpret
(`IsTypeHidden`, `TypeCodeCheckSumString`, `TypeSignatureCheckSumString`),
undiscoverable without walking raw source evidence by hand. Real evidence is
substantial, not marginal: 257 library interfaces in the M580 safety
fixture alone, 154 of them (60%) carrying real, non-empty text; smaller
real counts confirm the same shape in `estradege_m340.xef`,
`Escalier_Mecanique.XEF` and `MultiGrafcet_Coordination_V1_2026.XEF`. New
`LibraryInterface.description: str | None`, populated from that attribute
when its value is non-empty (an empty attribute is real -- most blocks have
none -- but is "undocumented", not "documented as blank", so both cases
collapse to `None` rather than distinguishing them); exposed in the CLI's
`library_interfaces` JSON output alongside `name`/`kind`/`parameters`. This
is a promotion of already-retained evidence to a first-class field, not a
new capture pathway, so it carries no ambiguity-handling of its own -- the
only judgment call is the empty-value normalization above. 3 new tests (a
real-shaped value, the empty/absent pair, a real-fixture count with an
example block's text checked by prefix); full suite (1435 tests) passed;
Ruff and Pyright passed.

DFB local-variable typing checkpoint (2026-09-23): a DFB local variable's
own `typeName` was resolved only against `known_datatypes` (a raw dict
lookup), unlike a top-level or resource tag's own type, which already goes
through the full four-way `_type_definition` (DDT / DFB instance / library
interface / Device DDT catalog) with an `unresolved_type` diagnostic when
none apply. This was a real, silent gap: real evidence surfaced while
scoping composite-initial-value promotion (a natural next step after the
composite initial value checkpoint above) shows a local variable is
routinely itself a DFB instance -- `IO_READAPI`'s `IO_READVAR` local is an
`IO_READVAR` instance, `P_BREAKER`'s `_count` local is its own counter DFB
-- exactly what a composite `instanceElementDesc` override targets one level
down, and what silently fell through as `data_type_definition = None` with
no diagnostic at all.

`_function_blocks` now runs in two passes: every DFB is registered by name
first (structure filled in after), so a local naming a DFB declared *later*
in source order resolves the same as one declared earlier -- the identical
forward-reference problem DDT members already solve with their own
two-pass capture, now solved the same way for DFB local variables. Locals
also gained the same array-wrapper stripping `_declare_variables` already
applies to top-level tags (`ARRAY[0..15] OF INT` resolves its `INT` element,
not the wrapper text -- `unresolved_array_type`, not `unresolved_type`) and
the same `unresolved_type` diagnostic top-level tags already get when
nothing applies. Real result: 33 real local variables that previously
resolved silently to nothing now classify correctly -- 30 as scalar arrays
(`unresolved_array_type`, matching top-level/DDT-member convention) and 3
as `Para_SCALING`, a genuinely new, unresolved member of the already-open
PID/regulation library family (joining `Para_PI`/`Mode_MH`/`Para_RAMP`).
`TOD`/`DATE`/`DT` (real evidence: `dt#1990-01-01-00:00:00` in a local's own
composite initial value) were added to the recognized elementary scalar set,
the same reasoning `BYTE`/`REAL`/`EBOOL`/`DWORD`/`UDINT`/`UINT` were added
under earlier. Top-level/resource tag classification counts are unchanged
(336 fb_instance / 131 library_type / 3 ddt / 301 catalog) -- this closes a
gap in local-variable typing specifically, not a regression in what already
worked. 4 new tests (forward-reference DFB-typed local, array-typed local,
genuinely-unknown-type local, plus an existing real-fixture count updated
from 26 to 29 unresolved_type occurrences); full suite (1438 tests) passed;
Ruff and Pyright passed.

Composite initial value promotion checkpoint (2026-09-23): the composite
initial value checkpoint above deliberately stopped at lexical-only capture.
With DFB local variables now fully typed (see the checkpoint above -- a
prerequisite this work is what actually surfaced that gap), each
`instanceElementDesc` node now resolves its own declaring member/local
variable and, for a leaf, promotes its scalar value the same conservative
way a top-level tag's own initializer already does.

`container` tracks what a node's own name is looked up against: a
`Datatype` for a struct member (`CompositeTagValueNode.member_definition`)
or an `AddOnInstruction` for a DFB instance's own local-variable override
(`local_variable_definition`, a new field -- a `Tag`, not a `DatatypeMember`,
so it needed its own slot rather than overloading one typed for the other).
An array-index child reuses its declaring array's own element type rather
than being looked up by name. Real evidence required one more
normalization: a project DDT member's `data_type_name` already arrives
array-unwrapped (existing `_datatypes` behavior), but the vendor Device DDT
catalog's own `data_type_name` does not (`T_U_DIS_SIS_IN_16`'s `CH_IN_A` is
literally `"ARRAY[0..7] OF T_U_DIS_SIS_CH_IN"`) -- element-type propagation
now always unwraps, the same normalization already applied to a top-level
tag's own type, which alone raised resolved member/local identities from
1207 to 1723 real occurrences.

`_declare_variables` now resolves a tag's own type before building its
composite value (reordered, not rewritten -- every diagnostic still reports
in its original relative position) so composite resolution can start from
the tag's already-resolved `function_block_instance`/`data_type_definition`/
`vendor_documented_type`. `uninterpreted_composite_initial_value` now fires
only when something under a tag's composite value remains genuinely
unresolved, mirroring the scalar initializer's own "nothing left
uninterpreted" standard, rather than unconditionally on every composite tag
as before.

Real result across all 214 composite-valued tags: 1723 of 1988 member/
local/array-index identities resolve, and 646 of 1376 leaf values promote.
What stays unresolved is the same kind of genuine, already-documented gap
promotion elsewhere in this project respects: TIME leaves (the same
deliberate restraint as scalar initializers, 65 occurrences), the
still-open PID/regulation library (`Para_PI`/`Para_RAMP`) and RIO-drop
Device DDT families (`T_M_DIS_ERT`/`T_M_COM_NOM`/`T_M_CRA_EXT_IN`/
`T_M_DROP_EXT_IN`, still no manual found), `TON` and other library (EFB)
instances with no captured internal structure to resolve a composite
override against, and a handful of Device DDT catalog sub-structures the
catalog itself doesn't transcribe (`T_U_DIS_SIS_CH_IN`'s own `V_OC`/`V_SC`/
`DIS_VALUE`, `MUID`/`RESERVED` -- already noted as left out when the catalog
was doubled). 99 of the 214 composite-valued tags still carry the
diagnostic; the other 115 now fully resolve. 8 new tests (struct member
resolution and promotion, array member elements, a DFB instance's own
local-variable override, a local variable that is itself a DFB instance one
level deeper, an unrecognized-type negative case, plus real-fixture checks
for both the existing 214-tag count and the new resolution/promotion
counts); full suite (1443 tests) passed; Ruff and Pyright passed.

Coil write evidence checkpoint (2026-09-23): the "multiple writers" half of
"Account for chart-control calls and multiple writers before execution
claims" was scoped before implementing anything, since the roadmap line
names chart/step state specifically. Checked directly: across the whole
reference corpus, no `INITCHART`/`SETSTEP`/`FREEZECHART` call ever targets a
chart or step already targeted by another call site within the same real
project -- every apparent duplicate (`G1`, `G2`, `G1_0`, ...) turned out to
be the identical project counted twice, once as a standalone export and
once as its own embedded ZEF. That variant stays unimplemented, the same
standard already applied to `parBranch`/`parJoint`: real, but not yet
buildable against.

Checking the *general* case (an ordinary declared tag written from more
than one routine/section, not just multiple pins in one diagram, which the
existing `shared_variables` grouping already covers) found real evidence
instead: `p_prev` is set from both `Init_Logic` and `Rising_Edge_Detection`
in the real escalator project; `databuffnoe`/`resetnoe` are each written
from two different sections in the real function15/function2 fixtures.

The `databuffnoe`/`resetnoe` writes are through a general FBD/EFB output
pin, not a coil -- and this project has a standing, three-times-repeated
rule that source pin direction alone does not prove memory read/write
effects (`GraphicalPin.direction`'s own field comment, the roadmap, and the
capture specification all say so independently). Claiming an "output" pin
writes its bound tag would be exactly that inference. A coil is different:
prior work already treats it as an unconditional write in its own
commentary (the coil operand binding checkpoint: "a coil cannot legitimately
write a step's active-state bit"), and IEC 61131-3 gives it well-established
LD semantics a generic block parameter direction does not carry. `resolve_
coil_write_evidence(controller)` is scoped to coils only on this basis --
`databuffnoe`/`resetnoe` are real evidence for a *different*, not-yet-scoped
capability (general read/write access semantics), not for this one.

New `CoilWriteLocation`/`TagWriteEvidence` (`analysis/graphical_bindings.py`)
group every resolved coil write by its target tag across a controller's
top-level programs, keyed by tag identity; Function Block bodies are
excluded on purpose -- a coil there writes the FB *definition*'s own local
tag, shared textually across every call-site instance, not a single
project-wide storage location the way a program-scope tag is. Every tag
with at least one coil write is retained, not only the multiple-writer
ones, matching how `shared_variables` already exposes full evidence rather
than only its own ambiguous cases; a new `multiple_coil_writers` diagnostic
fires only for tags with two or more distinct (program, routine) locations,
listing them, and never claims the writes are erroneous, redundant or
mutually exclusive -- a genuine PLC pattern (e.g. a conditional set in one
section, a conditional reset in another) is exactly what this surfaces.
Exposed in CLI JSON as `coil_write_evidence`, alongside the existing
`diagnostics` list. 4 new tests (single- vs multi-writer grouping, the
output-pin/FB-body exclusions, a real-fixture check); full suite (1446
tests) passed; Ruff and Pyright passed.

In passing, this also surfaced a larger, separate architectural gap not
acted on here: `analysis/tag_dependencies.py` (which backs the existing
L5X cause-and-effect/alarm-candidate analyses, and describes itself as
building "source-neutral tag cross-references") only reads a routine's
`LadderRung.text` -- an RLL mnemonic string only the L5X converter
populates. Control Expert's own Ladder series checkpoint (and CCW's
converter) populate `LadderRung.network` (the portable, already-structured
`LadderSeries`/`LadderInstruction` representation) instead, so CE and CCW
ladder logic is currently invisible to that whole analysis family, silently
skipped rather than diagnosed. Teaching `tag_dependencies.py` to also walk
`.network` when `.text` is absent -- using `LadderInstruction.operation`'s
already-portable `COIL`/`RESET_COIL`/contact semantics directly, more
precise than re-parsing mnemonic text -- would unlock cause-and-effect and
alarm-candidate analysis for Control Expert and CCW projects for free. That
is a substantially larger change touching shared, already-relied-on L5X
machinery, so it is recorded here as a scoped follow-up rather than
attempted under this checkpoint.

Structured ladder reference checkpoint (2026-09-23): the follow-up recorded
above is done. `tag_dependencies.py`'s `_ladder_calls`-based extraction only
ever read `LadderRung.text`; verified directly that Control Expert's own
`LadderRung(...)` construction site (`parsers/control_expert/ladder.py`)
sets only `network`, never `text` -- confirming the earlier finding was
real, not assumed. The same check on every `LadderRung(...)` construction
site in the codebase found CCW's own converter (`converters/ccw/project.py`)
in the identical position, and L5X's (`converters/l5x/program.py`) as the
mirror image: `text` only, `network` never set. The two are mutually
exclusive by construction everywhere, with zero real counterexample, so a
new `.network`-reading path can never double-count a reference `_ladder_calls`
already extracted from `.text` -- verified with a dedicated test (both set
on one rung; only the `.text`-derived reference appears).

New `_collect_structured_ladder_references` (`analysis/tag_dependencies.py`)
walks a rung's `LadderSeries`/`LadderInstruction` tree directly (recursing
into `LadderParallel` branches) whenever `.text` is absent and `.network`
is present, mapping `LadderOperation` to `TagReferenceAccess` directly --
`NORMALLY_OPEN_CONTACT`/`NORMALLY_CLOSED_CONTACT` to `READ`,
`COIL`/`SET_COIL`/`RESET_COIL` to `WRITE` -- more precise than `_ladder_calls`'s
own mnemonic-text regex matching, since `LadderOperation` is already the
portable classification this project assigned at capture time. `UNSUPPORTED`
(an instruction shape with no portable meaning yet) and an instruction with
no operand produce neither a resolved nor an unresolved reference at all --
not even "unresolved," since the access kind itself is unknown, not just
the operand's target.

Real result: 12 real structured-ladder references (5 `coil`, 5
`normally_open_contact`, 1 `reset_coil`, 1 `normally_closed_contact`) across
the corpus now flow through `build_tag_dependency_graph` -- previously
silently absent, not diagnosed. `p_prev` in the real escalator project
(the same tag the coil write evidence checkpoint above found) now resolves
its full read/write picture through the shared, general-purpose machinery
too: a `reset_coil` write in `Init_Logic`, a `normally_closed_contact` read
and a `coil` write in `Rising_Edge_Detection` -- richer than the CE-specific
coil write evidence pass above, which only ever saw the two coil writes,
not the read. `build_alarm_trip_candidate_report`/`build_cause_effect_
candidate_report` were smoke-tested directly against the real escalator
project end to end (ran cleanly, zero candidates -- this fixture's tag
names carry no alarm/trip lexical evidence for that separate heuristic to
match, not a defect in this change). 5 new tests (read/write resolution,
the text-wins-over-network non-double-counting guard, parallel-branch
recursion, the unsupported/unbound-operand exclusion, a real-fixture
check); full suite (1451 tests) passed; Ruff and Pyright passed, including
the CCW-specific test subset (23 tests), since CCW's own ladder rungs are
now processed the same way for the first time too.

`nin` extensible parameter checkpoint (2026-09-23): a real diagnostic
survey across the whole corpus (`unresolved_library_pin`, 20 occurrences)
led here -- all 20 were extensible-family pins the existing Extensible-
parameter checkpoint's own mechanism did not cover: `MAX`/`MIN`/`LT`/`LE`/
`GE`/`EQ` (and their `_REAL`/`_INT`/`_TIME` variants) and `LOOKUP_TABLE1`,
all real calls in `estradege_m580-safety.xef`. Their own `IN1`/`XIYI1`
parameter never carries the literal `"(Extensible)"` comment text the
existing mechanism keys on; instead it reads `"Input 1..32"`,
`"Input (IN0..IN30)"` (the `MUX` family), or has no extensibility hint in
its own text at all (`LOOKUP_TABLE1`'s `"X/Y coordinate support points"`).

Surveying every one of the 268 real library interfaces in the corpus for a
hidden `nin` (input count) parameter -- the same structural marker the
original Extensible-parameter checkpoint noted in passing but did not key
on -- found it a strictly more general, equally reliable signal: every
interface carrying the `"(Extensible)"` marker also declares `nin` (zero
counterexample), while 21 real interfaces declare `nin` with no marker
text at all. `_extensible_templates` now registers a template on either
signal -- the marker check is kept, not replaced, since a hypothetical
future template could carry the marker without `nin` the way none observed
so far does the reverse -- and only for a parameter's own `input` side,
matching every real occurrence (no evidence of an extensible output family
paired with a hidden count parameter). This is exactly the same kind of
generalization-by-declared-structure this session already applied to
chart-control calls (typed parameters, not block names) and DFB local
variables (full type resolution, not a raw dict lookup).

Real result: all 20 previously-`unresolved_convention` pins now resolve
`matched_extensible`; `unresolved_library_pin` drops from 20 to 0 across
the whole corpus. 4 new tests (the `nin`-without-marker shape, a non-first-
parameter template alongside an unrelated unresolved output pin staying
correctly unresolved, a real-fixture check covering all 7 newly-resolved
block types); full suite (1454 tests) passed; Ruff and Pyright passed.

Label/jump statement checkpoint (2026-09-24): the step-state-inside-ST
backlog item asked, as a prerequisite, whether `twinforge.structured_text`
(built for L5X/Logix ST) generalizes to Control Expert's own ST -- an
investigation, not an assumption. It does: `parse_structured_text` already
ran against every real CE ST body via `tag_dependencies.py`'s existing
`_collect_structured_text_direct_references` (itself vendor-neutral,
operating on the shared `routine.structured_text` field), but a direct
corpus-wide measurement found real cost: 1362 real statements, 271 (20%)
`UnsupportedStatement`, concentrated almost entirely in one fixture
(`estradege_m580-safety.xef`, 67 real ST bodies).

Categorizing all 271 found one dominant root cause behind roughly 83% of
them: Control Expert's own legacy GOTO-style control flow -- a labeled
program point (`CMD_ACTION:`, standing alone, unrelated statements
following it in the same list) and `JMP <label>;` -- which the parser had
no grammar for at all. A bare label swallowed not just itself but
everything after it up to the next recovery point into one garbled
`UnsupportedStatement` blob, real evidence a single diagnostic count
understated the true cost. New `LabelStatement`/`JumpStatement` syntax
nodes, a new `TokenKind.COLON` (a bare `:`, distinct from the existing
`:=` token, which the lexer already checks first), and two additions to
`_statement()`: `JMP` as a keyword (matching how `IF`/`WHILE`/`EXIT`
already are), and a 2-token lookahead (`IDENTIFIER` then `COLON`) checked
*before* the generic expression path, since a bare `NameExpression`
followed by an unexpected `:` is exactly what previously failed. A label
is a no-op marker only -- statements after it in the same list still
execute in order; resolving a jump's target against an actual
`LabelStatement` (and what that implies for reachability) is retained as
evidence only, not attempted here. `NeutralOperationKind` gained matching
`LABEL`/`JUMP` entries in `semantics.py` so both are properly classified
rather than falling through to `UNSUPPORTED` there too.

Real result measured directly: 271 unsupported statements dropped to 117
(all still in the same one fixture) -- a 57% reduction from a single,
well-evidenced root cause. What remains is a second, separate, already-
measured gap (a `%`-prefixed direct/system address inside an ST
expression, e.g. `%S18`, `RESET(%S18)`, `_alarms.5 := %S18`, 42
occurrences) and a residual "other" category (a `FOR` loop, a handful of
other shapes) -- neither attempted here, recorded as its own follow-up in
the roadmap rather than bundled into this change. 6 new tests (label
standing alone before an unrelated statement, label immediately followed
only by a comment, a malformed `JMP` with no label staying diagnosed
rather than guessed, the lossless-reconstruction contract holding for the
new tokens, a semantics-layer test confirming `LABEL`/`JUMP` get their own
`NeutralOperationKind` rather than `UNSUPPORTED`, a real-fixture check
with exact counts -- 37 labels, 20 jumps, 117 remaining unsupported, all
in `estradege_m580-safety.xef`); full suite (1460 tests) passed; Ruff and
Pyright passed.

Direct-address expression checkpoint (2026-09-24): the remaining gap the
label/jump checkpoint identified and deferred -- a `%`-prefixed IEC direct/
system address (`%S18`, `%SW12`, `%S6`, 11 distinct real addresses) used
inside an ST expression, not just the isolated LD/FBD/section-condition
contexts this shape was already recognized in (`ExpressionSpec.direct_
address`). The shared lexer previously tokenized `%` one character at a
time as `UNKNOWN`, failing whatever statement contained it -- a real call
argument (`RESET(%S18)`), assignment RHS (`_alarms.5 := %S18`), and
comparison operand (`(%SW12 = 16#A501) and (%SW13 = 16#501A)`) all hit
this.

New `TokenKind.DIRECT_ADDRESS` (lexed as `%` followed by letters then
digits; a malformed shape, e.g. `%6` with no letters, is diagnosed --
`malformed_direct_address` -- not silently guessed at) and a matching
`DirectAddressExpression` syntax node, deliberately separate from
`NameExpression` since a direct address is not a declared symbol and must
never be treated as one downstream -- confirmed by inspection, not just
assumption: `tag_dependencies.py`'s `_direct_expression_operands` already
falls through to its `return ()` default for any expression kind it
doesn't explicitly recognize, so the new node type is automatically
excluded from tag-reference extraction with no changes needed there. A
`.digit` bit-select suffix (the shape `ExpressionSpec.direct_address`'s
own regex allows) has zero real ST occurrence, so it is deliberately left
to the existing generic member-access grammar (`%SW12.5` would parse as
`DirectAddressExpression("%SW12")` plus a `MemberExpression(".5")`) rather
than folded into the token -- proportionate to evidence, not the broadest
shape possible.

Real result: unsupported statements in `estradege_m580-safety.xef` (the
only fixture with substantial ST) dropped from 117 to 71. In passing, a
second, separate, real gap surfaced and is deliberately not fixed here:
`00CMA01EA900` and similar digit-led identifiers (a real industrial KKS
tag-naming convention, dozens of real occurrences in `Sim_ST`) are
currently mis-tokenized by the shared lexer's own numeric-literal path
(`_consume_literal_tail` accepts letters, originally for typed literals
like `16#FF`) as a `LiteralExpression` rather than a name -- this does not
fail to parse, so it never appeared in the unsupported-statement count,
but it is a real correctness gap distinct from anything measured so far;
recorded as its own roadmap follow-up rather than guessed at a fix here.
4 new tests (a call argument and an assignment RHS, a direct address
nested inside a parenthesized binary comparison, the malformed-shape
diagnostic, lossless reconstruction); full suite (1464 tests) passed;
Ruff and Pyright passed.

Digit-led identifier checkpoint (2026-09-24): the follow-up the direct-
address checkpoint recorded above. `00CMA01EA900` and 41 other real KKS
(power-plant equipment identification standard) tag names were mis-
tokenized by the shared lexer's own numeric-literal path -- `_consume_
literal_tail`'s continuation set (alnum/`_`/`#`/`:`) happily consumes
letters too, originally so a based/typed literal's own tail (`16#FF`,
`T#10s`) could be lexed from one entry point, with the side effect of
also swallowing a digit-led name whole as one `LITERAL` token. This never
failed to parse -- `P_SIM := %S6 and SIM and 00CMA01EA900;` parsed
cleanly before this fix too -- so it never showed up in any unsupported-
statement count; it silently mistyped a real tag reference as a literal
value instead, a correctness gap distinct from a parse failure.

`_numeric_literal` now consumes the alnum/`_` run first (without `#`,
`:`, or the decimal/exponent tail yet) while tracking whether any letter
appeared, then decides: a `#` immediately following still wins
unconditionally and reads as a based/typed literal, exactly as before --
real evidence backs this ordering too, since no real KKS name is ever
followed by `#`; otherwise a letter anywhere in the run means the token
is `IDENTIFIER`, matching `ExpressionSpec.identifier`'s own established
rule for CE's pin/contact expressions ("a name may also start with
digits... as long as it contains at least one letter/underscore
somewhere... a token that is purely digits is a numeric literal... and
must keep failing this pattern"); a purely-digit run still falls through
to the original `_consume_literal_tail` call for its decimal/exponent
tail, unchanged. `_primary()` needed no changes at all -- `TokenKind.
IDENTIFIER` already becomes a `NameExpression` regardless of how it was
produced.

Real result: 42 distinct real digit-led names across the corpus
(`00BBA01GS001`, `00CMA01GS100`, ...) now resolve as `NameExpression`
instead of `LiteralExpression`; unsupported-statement counts are
unaffected (71, unchanged), confirming this was purely a mistyping fix,
not a parse-failure fix. 5 new tests (the real KKS shape resolving as a
name, a pure-digit token still correctly staying a literal, a based/typed
literal still taking priority when `#` follows a digit-led prefix,
lossless reconstruction); full suite (1468 tests) passed; Ruff and
Pyright passed.

ST step-state reference checkpoint (2026-09-24): closes the step-state-
inside-ST backlog item now that the ST parsing foundation is solid. Real
evidence, confirmed unchanged since it was first noted: exactly 3
occurrences, `G1_0.X`/`G1_1.X`/`G1_2.X` in `G1_Voyants`'s `IF G1_0.X THEN
... ELSIF G1_1.X THEN ... ELSIF G1_2.X THEN ...` (`MultiGrafcet_
Coordination_V1_2026.XEF`). This already parsed cleanly before this
checkpoint (0 diagnostics, `MemberExpression(target=NameExpression("G1_0"),
member="X")`) -- the gap was purely semantic: `tag_dependencies.py` had no
concept of an SFC step at all, so all three showed up as
`UnresolvedTagReference(identifier="G1_0.X", ...)`, indistinguishable from
a genuinely undeclared tag.

`build_tag_dependency_graph` gained optional `step_names`/
`ambiguous_step_names` parameters (a project-wide step registry, the exact
same shape `resolve_graphical_bindings` already builds for LD contacts) --
omitting them changes nothing for an existing caller with no step evidence
to offer, verified by a dedicated test. Inside `_collect_structured_text_
direct_references`, an extracted operand matching `<name>.X`/`<name>.x`
is checked against the step registry *before* falling through to ordinary
`_collect_operand` tag resolution -- but only after confirming `<name>`
is not already a declared tag, the identical precedence already
established for chart-control calls (a same-named tag always wins over a
program/step interpretation). New `StepStateReference`/
`AmbiguousStepStateReference` result types, kept deliberately separate
from `TagReference` rather than conflated with it: a resolved SFC step is
not a `Tag` object, and forcing one into the other's shape would be a
type mismatch dressed up as a simplification, the same reasoning that
already produced `local_variable_definition` as its own field alongside
`member_definition` in the composite initial value work.

This is analysis-layer only: `tag_dependencies.py` is not currently
called anywhere in Control Expert's own CLI pipeline at all (it backs
L5X's `cli/l5x_report.py`/`cli/review_validation.py`), the same standing
already established by the structured ladder reference checkpoint's own
smoke tests. Giving Control Expert an equivalent tag-dependency/cause-
effect CLI surface is a separate, materially larger feature, not attempted
here. Real result: all 3 real occurrences now resolve as
`StepStateReference` instead of `UnresolvedTagReference`. 5 new tests
(basic resolution, the ambiguous-step-name guard, the declared-tag-wins
precedence case, the opt-in/no-behavior-change-by-default guard, a
real-fixture check with exact step/routine names); full suite (1473
tests) passed; Ruff and Pyright passed.

Tag dependency graph wiring checkpoint (2026-09-24): the ST step-state
reference checkpoint above deliberately left `build_tag_dependency_graph`
uncalled from Control Expert's own pipeline. `parse_project` now calls it
directly -- reusing the exact `step_names`/`step_counts` already built
earlier in the same function for LD contact and chart-control-call
resolution, no new evidence-gathering needed -- and stores the result on
`ParsedProject.tag_dependency_graph`, exposed in CLI JSON via the existing
`tag_dependency_graph_data` helper (already shared with L5X's own report
CLI) under a new `tag_dependency_graph` key, alongside the existing
`coil_write_evidence`. A new `ambiguous_step_state_reference` diagnostic
mirrors `multiple_coil_writers`'s own pattern -- real evidence stays at
zero ambiguous cases in the corpus, but the mechanism is exercised by a
synthetic test.

This is deliberately *not* the L5X report bundle (alarm/cause-effect/
IO-list/module-schedule/functional-description, `cli/l5x_report.py`) --
that is a separate, materially larger, already-mature multi-report system
built over many prior sessions; giving Control Expert an equivalent is its
own future project, not a natural extension of today's step-state work.
This checkpoint only wires the dependency graph itself (the same one the
step-state checkpoint already built) into evidence a CE user can actually
see today, without inventing a new report format.

Measuring the real corpus through the now-wired pipeline surfaced one more
finding, recorded as its own backlog item rather than chased here:
`FREEZECHART(G2, NOT Run_G2)` in `MultiGrafcet_Coordination_V1_2026.XEF`'s
`FREEZE` program is a chart-control call made *from ST*, not a graphical
diagram -- the existing `_call_reference_kind` mechanism (declared
parameter type, not block name) only ever inspects `GraphicalPin`/
`GraphicalObject`, so `G2` still shows up as a plain
`UnresolvedTagReference` rather than a program reference. Real result:
295 tag references now resolve corpus-wide (unchanged from before this
checkpoint -- this wiring surfaces evidence, it doesn't change what
resolves), 6 step-state references (the 3 real `G1_0`/`G1_1`/`G1_2`
occurrences, doubled by the standalone/embedded pair as usual), 210 still
unresolved (a mix of genuinely undeclared symbols, the `FREEZECHART`
program-name gap just noted, and other not-yet-categorized shapes). 4 new
tests (full-pipeline resolution, the ambiguous-reference diagnostic, a
CLI JSON end-to-end check, a real-fixture check); full suite (1477 tests)
passed; Ruff and Pyright passed.

`setCoil`/new-corpus checkpoint (2026-09-24): the user pointed at
`github.com/sayahali/conveyor-automation`, a public third-party repository
carrying a real Control Expert M340 export (`ali conv.zef`) and, uniquely
for this corpus, a PDF printout of the same project's own ladder diagrams
(`documentation convoyeur.pdf`) -- independent, human-authored ground
truth for what a real ladder network's visual layout looks like, not just
its XML. See the new-corpus entry in the capture specification for full
provenance, license status (none stated -- kept local-only, never
committed) and detail.

The PDF itself resisted this project's own text/page tools (password-
protected), but `pdftoppm` (poppler) rendered every page to a lossless PNG
without needing the password at all, which is how it was actually read.
Cross-checking the rendered pages against the parsed model surfaced one
immediate, narrowly-scoped real bug: `typeCoil="setCoil"` (4 real
occurrences) was simply missing from `_COIL_OPERATIONS`, even though
`LadderOperation.SET_COIL` already existed in the model as `resetCoil`'s
natural counterpart. Fixed by adding the one missing dictionary entry (one
line); all 4 real rows now resolve correctly, and
`unresolved_ladder_instruction` drops to zero for this fixture.

The same fixture also surfaced a real, latent test-design bug, unrelated
to Control Expert parsing itself: five real-fixture tests (in
`test_control_expert_project.py`/`test_graphical_bindings.py`) skip
correctly when specific named fixtures are absent, but then iterate
`glob.glob("reference/control-expert/*")` to do the actual work --
processing *every* file present, not just the ones their exact-count
assertions were calibrated against. Adding this new, legitimate local
fixture (per the artifact policy, `reference/` is the normal place for
exactly this) broke three of them immediately, since it added real `%M12`/
`%M15`/task/DFB evidence of its own that those counts never accounted for.
Fixed by iterating the existing canonical `_REFERENCE_CORPUS` list (already
defined and already used for the skip check) instead of a wildcard glob,
in all five affected tests -- the same "don't silently run against more
than intended" discipline the earlier broken-skip-check fix already
established, just for the iteration itself rather than the skip guard.

The fixture's real value is bigger than the one bug it fixed: it is dense
with `shortCircuit`/inline-`FFBBlock` evidence the corpus never had before
(at least 20 real `SR` Set-Reset latch instances, several `TON`/`CTU`
instances, almost all `enEnO="false"` -- no `EN` pin at all). The existing
`resolve_ladder_pin_conditions` mechanism is `EN`-only by construction, so
none of these resolve through it. Cross-checked visually against the PDF
(page 28): the real, consistent shape is two independent contact rows
landing on one block's `S1` and `R` inputs separately, with the block's
own output feeding a coil or (page 25) chaining into a second block's own
input -- a materially harder problem than the single-`EN`-landing case
already solved, needing its own row-to-pin mapping design (by declared
parameter order and row offset from `objPosition`, not assumed) plus
block-to-block chaining. This is genuinely new evidence for the
`shortCircuit`/`VLink` backlog item -- the "needs more fixtures" half of
its own stated blocker is now met -- but the design and implementation
itself is deliberately not attempted in this pass; recorded as a real,
scoped, ground-truth-backed follow-up rather than guessed at under time
pressure. 2 new tests (the `setCoil` shape resolving correctly, a
malformed-shape guard remains unaffected); full suite (1477 tests) passed;
Ruff and Pyright passed.

Multi-pin `shortCircuit`/`FFBBlock` investigation (2026-09-24, no code
change): a direct follow-up attempt on the backlog item above, using the
same `sayahali/conveyor-automation` fixture. Read-only investigation;
nothing in `ladder.py` changed. Recorded in detail so the next attempt
starts from what was actually learned here, not from zero.

**Confirmed, and now independently re-verified beyond the original
checkpoint's own evidence**: the parser's internal row counter (advanced
one per `typeLine`, by `nbRows` per `emptyLine`) matches every real
`FFBBlock`'s own `objPosition/posY` exactly. Checked directly against all
12 `FFBBlock` instances in this fixture (`SR_8`, `SR_9`, `TON_23`, `SR_2`,
`TON_24`, `SR_3`, `TON_25`, `SR_4`, `TON_26`, `SR_5`, `TON_28`, `SR_7`) by
independently replicating the row-counting logic outside the parser and
comparing to the raw XML's own `posY` attribute -- zero mismatches. This
was already relied on for the `EN`-landing case; it is now confirmed to
hold generally, not just for the cases already exercised.

**The PDF is not ground truth for this specific file.** The instance the
PDF visually shows with the cleanest two-separate-input-rows shape
(`SR_33`, page 28 of `documentation convoyeur.pdf`) does not exist
anywhere in `ali conv.zef`'s own XML -- confirmed by direct string search.
The PDF documents a different revision of the same project. It remains
useful as general reference for what Control Expert ladder wiring looks
like, but nothing in it can be cross-checked instance-by-instance against
this particular file's own XML, which is what an implementation would
actually need to match exactly.

**The real shape in this file is narrower, and different, from what the
PDF suggested.** Every `SR` block that is actually wired (`SR_2`, `SR_3`,
`SR_4`, `SR_5`, `SR_7` -- one per `TON_2x`/`TON_2x+1` pair) takes the form
`<shortCircuit><VLink/><FFBBlock .../></shortCircuit>`, with *no contacts
of its own* in that row (real example, `SR_2` at row 21: `empty(4) |
shortCircuit(VLink,FFB[SR_2]) | HLink(1) | empty(2) | HLink(1) |
coil[resetCoil:M1_S1]`). Since there is nothing upstream in the same row
to carry a condition, and the immediately preceding rows (19: `TON_23`,
20: a lone `HLink(7)`) are `TON_23`'s own EN/IN/output rows, the strong
implication is that `SR_2.S1` is fed by `TON_23`'s own `Q` output, not by
a second row of contacts -- block-to-block chaining, confirming the
concern already raised in the previous checkpoint, not the "two
independent contact rows" shape the PDF seemed to show.

This is a materially different, and *not yet understood*, geometry
problem: resolving it needs the column/width semantics of a block's
*output* side (where `Q`/`ENO`/`ET` sit relative to `posX`+`width`), which
nothing so far has verified against real evidence the way the row/`posY`
correspondence was just confirmed. Attempting a rule here without that
verification would be exactly the kind of guess this project does not
make.

**A real negative case, worth keeping in mind for any future attempt**:
`SR_8` and `SR_9` are also `shortCircuit`/`FFBBlock`-shaped (`SR_8` at row
1, `enEnO="false"`, `S1`/`R` both declared) but have *no* wire landing on
them at all -- the rows immediately around them are unrelated, disconnected
rungs. Being wrapped in `shortCircuit` does not by itself mean a real
input condition exists; a future implementation needs the same "confirmed
clean landing, not merely present" discipline the `EN` case already
applies, generalized correctly, or it will produce false positives on
exactly this shape.

Net position: the evidence gap for `shortCircuit`/multi-pin `FFBBlock`
landing is real and substantial, but the problem itself is now understood
to be block-to-block output chaining, not the simpler two-row-input
pattern originally hypothesized from the PDF alone. No code changed; no
tests added. Still recorded as open in the roadmap.

`FFBBlock` column-width checkpoint (2026-09-24): the user asked to re-check
the corpus already in hand (not new external material) for anything that
might help the still-open block-to-block chaining problem above. It split
into two outcomes, one real fix and one dead end, and both are worth
recording precisely so neither gets re-attempted or misremembered as more
than it is.

The fix: `resolve_ladder_pin_conditions` explicitly did not know an
`FFBBlock`'s own column width -- the row scan simply stopped at the first
one, treating everything past it as unknown rather than known-dead (see
the module docstring's prior wording, and the previous multi-pin
investigation entry above). Measuring every `FFBBlock` row's leading and
trailing cell counts across six independent real projects
(`Escalier_Mecanique.XEF`, `escalier_mecanique.zef`,
`MultiGrafcet_Coordination_V1_2026.XEF`, `tsaii_multigrafcet_final_v1.zef`,
`function15.zip`, `function2.zip`) gives the same sum, `9`, in every row,
regardless of block type (`TON`/`SET`/`RESET`/`ADD`/`MBP_MSTR`) or pin
count (1 to 6). Every one of those networks' `LDSource nbColumns` is also
identically `"11"`. `11 - 9 = 2`: a block always occupies exactly two grid
columns; pin count grows its row span only, never its column span. Fixed
in `ladder.py` -- the row scan now continues past a resolved or unresolved
`FFBBlock` using this known width instead of abandoning the row, marking
the block's own start column so later elements still can't wrongly jump
across it. This changed no existing resolved result (hand-traced and
confirmed by the unchanged `function15`/`function2` `en_condition(...)`
assertions in `test_optional_real_function15_short_circuit_conditions`);
it closes a previously-flagged gap and is exercised by two new synthetic
tests, one proving the continuation itself (a wire starting after a first
block still reaches a second one, impossible before) and one proving the
new obstruction it enables (a block's own footprint correctly blocks a
wire trying to reach past it). 275 tests pass; Ruff and Pyright pass.

The dead end: whether this also explained the open block-to-block
*output* chaining question. In `function15.zip`/`function2.zip`'s
`resetnoe` program, `.5`/`ADD` (`posX="2"`, width 2, right edge at column
4) sits with a `VLink` at column 4 that continues on to land unconditionally
on `.4`/`SET`'s `EN` pin -- exactly the shape a `TON.Q`-feeds-`SR.S1` style
chain would produce, and the first read of it looked like real evidence.
Tracing every row back from column 4, row by row, shows it is not: that
wire independently originates from its own `shortCircuit(VLink, HLink
nbCells="4")` three rows earlier (an unconditional bridge with no contact
of its own), fully explained without reference to the `ADD` block at all.
It merely happens to sit at the same column because of where the block was
placed in the grid -- a coincidence, not a connection. No fixture in the
corpus provides real evidence of an `FFBBlock`'s own output pin feeding
anything. The backlog item stays open; this was checked and ruled out, not
skipped.

`FFBBlock` output-edge evidence, real but inconclusive (2026-09-24): asked
to keep digging the corpus for the same open question, this time with a
precise, corpus-wide, corrected-width scan for any wire that appears to
originate fresh at a block's own output edge (`posX + 2`, some row within
`[posY, posY + max(inputs, outputs))`) with nothing marking that column in
the row immediately above it -- a "birth" test, deliberately excluding the
function15/function2 false positive above by construction (that wire had a
marker one row up, so it fails this test and correctly does not appear
here).

Five real hits, all identical in shape: `TON_23`, `TON_24`, `TON_25`,
`TON_26`, `TON_28` in `sayahali_conveyor_ali_conv.zef`, each a `TON`
(`enEnO="true"`, declared `inputVariable` order `EN, IN, PT`;
`outputVariable` order `ENO, Q, ET`). Every one launches a fresh one-cell
`HLink` at exactly `posX + 2`, row `posY + 2`, immediately followed by a
`resetCoil` (`M1_S1`, `M2_S1`, `M1_S1`, `M3_S1`, `M4_S1` respectively --
distinct per instance, ruling out a shared/independent circuit
coincidence the way the earlier false positive was ruled in). This is
real, repeated, structurally clean evidence that a block's own output can
originate a wire in exactly the way its own input side already does.

What it does not establish: *which* output pin. Row offset 2 from `posY`
is the third declared output in this evidenced case, `ET` -- a `TIME`
value, which cannot legally drive a boolean `resetCoil` in Control Expert
(IEC 61131-3 type-checked). Either the naive "row offset equals
declaration-index" rule that already holds for input landing does not
carry over unchanged to the output side (something else determines which
of `ENO`/`Q`/`ET` gets which row, not yet evidenced), or something about
this shape has been misread. No other block type in the corpus shows this
"fresh birth at the output edge" shape at all (checked
`Escalier_Mecanique.XEF`, `MultiGrafcet_Coordination_V1_2026.XEF`,
`function15.zip`, `function2.zip`, `tsaii_multigrafcet_final_v1.zef`), so
there is no cross-type case (e.g. an unambiguously-numeric block output
feeding a numeric input) to disambiguate the row-to-pin rule the way
having several block types helped confirm the row/`posY` correspondence
and the column-width constant earlier today. One incidental near-miss:
`MultiGrafcet_Coordination_V1_2026.XEF`/`tsaii_multigrafcet_final_v1.zef`'s
`.3` (`SETSTEP`) shows the same "fresh birth" shape at its own output edge,
but the wire dead-ends into nothing (`following=[]`) -- not useful as
corroborating evidence either way.

Not implemented. Attaching a specific output pin name to this connection
without resolving the type-compatibility contradiction would be exactly
the kind of guess this project does not make; the structural fact (a real
wire, real per-instance targets, corpus-repeated 5/5) is recorded here for
whoever picks this up next, separate from the unresolved pin-identity
question.

`enEnO="false"` anchor-row landing checkpoint (2026-09-24): the user
supplied a page from `sayahali_conveyor_ali_conv.zef`'s own PDF
documentation showing `SR_4`'s real rendering -- `S1` (input) and `Q1`
(output) share the block's top row, no separate `EN`/`ENO` row exists in
the picture at all. That single image did what three rounds of XML-only
analysis in this investigation could not: settle whether an
`enEnO="false"` block's anchor row is `EN`'s row (just hidden, still
reserved) or the first pin that's actually rendered. It's the latter.

Implemented two things together in `ladder.py`. First, `shortCircuit` can
wrap an `FFBBlock` directly (`<shortCircuit><VLink/><FFBBlock/></shortCircuit>`),
not just a contact/`HLink` -- previously fell through to
`unresolved_ladder_short_circuit` as a malformed shape. This terminates
the wire on the block immediately, no "continues one row past" ambiguity
to check (unlike the far-arriving VLink-chain case already shipped).
Second, a new `landing_pin_name()` helper generalizes the anchor-row rule:
`EN` when `enEnO="true"` (unchanged), or the block's second declared input
when `enEnO="false"` -- used by both the new direct-wrap case and the
existing far-arriving case, so a wire that reaches an `enEnO="false"`
block's anchor row via a long `VLink` chain now also resolves correctly
instead of being silently skipped.

Rechecking the raw XML for `SR_8`/`SR_9` while implementing this turned up
a cleaner explanation than the earlier "shortCircuit/FFBBlock-shaped but
unconnected" description: they are not `shortCircuit`-wrapped at all --
bare, unwrapped `FFBBlock` elements sitting alone in their row. That is a
structurally distinct shape, not an edge case of the shape being
implemented, so the new rule cannot land on them regardless of any
`active`-wire bookkeeping; confirmed directly (both stay unresolved).

Real corpus result, `sayahali_conveyor_ali_conv.zef`: all five wired `SR`
instances (`SR_2`, `SR_3`, `SR_4`, `SR_5`, `SR_7`) now resolve `S1`
unconditionally (`shortCircuit(VLink, HLink)`-style empty condition, same
as the already-evidenced unconditional case); `SR_8`/`SR_9` correctly stay
unresolved. `R` (the block's second wireable input, one row below `S1`)
was checked directly against all five real instances and found genuinely
unwired in every one -- a real, checked negative, not a gap in the
implementation; there is simply no positive example in this fixture to
confirm a row-offset rule for it.

New tests: four synthetic (unconditional landing, landing with a leading
contact condition, the bare-block negative case, and a malformed case with
no second declared input) plus one real-fixture test asserting all seven
`SR` instances' `S1` state exactly. 280 tests pass (up from 275); Ruff and
Pyright pass.

`FFBBlock` output-edge padding-row checkpoint (2026-09-24): same
conversation, immediately after the anchor-row fix above. Asked the user
directly why the earlier `TON` output-edge finding didn't fit the naive
row-offset reading (`ET`, a `TIME` value, at `posY+2` -- type-incompatible
with the `resetCoil` it fed), and got back two things: the wired pin is
`Q`, and `ENO` is routinely left unconnected in real projects unless
there's a specific reason to chain on it (general practice, not a
Control-Expert-internal detail).

That confirmed *what* the pin is but not *why* it sits at `posY+2` instead
of `posY+1` (`Q`'s own declared index). Reconciling all four rows around
`TON_23` (`posY+0` empty, `posY+1` empty, `posY+2` wired, `posY+3` empty)
against a single rule: the output side reserves one blank row before its
first pin, so output pin *i* sits at `posY + 1 + i`, not `posY + i` the
way input pins do (`EN` confirmed at exactly `posY+0`, already shipped).
Cross-checked against a corpus-wide structural fact with zero exceptions
across all nine distinct block shapes in the corpus: `height ==
max(inputs, outputs) + 1`, always -- consistent with exactly one spare row
sitting specifically at the top of the output side.

Not implemented, on purpose: the formula is only unambiguous where
`outputs >= inputs` (`TON`, `SET`, `RESET`, `MBP_MSTR`); the corpus's four
`inputs > outputs` shapes (`ADD`, `SR`, `INITCHART`, `SETSTEP`) make a
different, untested prediction under a competing formula, and none of
their real occurrences in the corpus show a wired output to check against
(checked directly -- `ADD`/`MBP_MSTR` in `function15.zip`/`function2.zip`
show no "fresh birth" output wire at all). Representing even the confirmed
subset also needs a small model addition first (`LadderInstruction.operand`
is a plain tag-name string today; a block-output reference is a different
kind of evidence, not a variable name) -- not started this pass.

`effectiveParameter`: the output-edge puzzle is narrower than it looked
(2026-09-24). Asked to keep digging the same question (which pin an
`ADD`/`SR`-type block's wired output row corresponds to), the user's
request to search externally for a genuine new LD fixture turned up
several real repos (`estradege/controlexpert`, `pupenasan/PACFramework`,
`anythingwithawire/unityview`, `jeanartics/reflex`, `tomha85/devagent`),
but the one that actually mattered was a synthetic test fixture inside
`tomha85/devagent` (MIT licensed) showing `outputVariable` can carry an
`effectiveParameter` attribute, the same way an `inputVariable` can be
bound to a literal (`PT effectiveParameter="t#3s"`, already known). That
sent a direct check back into the *existing* corpus, which had never been
searched for this attribute on outputs before:

`effectiveParameter` on a real `outputVariable` is common, not rare --
found on hundreds of instances across `Escalier_Mecanique.XEF`
(`TON_0.Q -> Timer_Done`), `function15.zip`/`function2.zip` (`TON_2.Q ->
timedoutnoe`, `TON_2.ET -> tcptimernoe`, `.4(ADD).OUT -> abortnoecount`,
`.5(ADD).OUT -> resetnoecount`), and, directly answering the open
question, `estradege_m580-safety.xef` (`Sim_W505_DA(SR).Q1 ->
Sim_W505_STOP`, `SIM_TRIPW505(SR).Q1 -> Sim_W505_OK`, plus a dozen more
real `S_SR` instances). This is a *named-variable* binding on the pin
itself -- no drawn wire, no grid position needed at all to resolve it.

Better still: it turns out to already be fully implemented.
`graphical.py`'s pin construction already reads `effectiveParameter` into
`GraphicalPin.expression` for every pin, input or output, with no
LD/FBD distinction -- confirmed directly (`grep effectiveParameter
src/twinforge/`, one call site, already wired for outputs).

This reframes the actual scope of the remaining gap. It is not "how do
`ADD`/`SR`-type block outputs get resolved" -- that's already solved for
every instance that uses a named-variable binding, which the evidence
above suggests is the common case. It is specifically: how does a *drawn
ladder wire with no `effectiveParameter`* reach one of these pins --
confirmed to be the shape actually used by `sayahali_conveyor_ali_conv.zef`'s
`TON_23`-`TON_28` (`expression=None` checked directly on all three output
pins of `TON_23`, ruling out any named-variable binding there). That is a
real, narrower, and apparently rarer shape than originally framed, still
open, still without a second `n_in > n_out` example to test the row
formula against.

Block-output-fed coil checkpoint (2026-09-24): told to keep pushing on the
same drawn-wire question, `apexsotjo-blip/control-expert-mcp`'s
`LD_1_Heating.xml` test fixture (no license declared; kept local-only,
never committed) turned up a second, much denser confirmation of the
`posY+1+i` output-row formula -- a custom `Heating` DFB with 4 inputs, 7
outputs, six real outputs all wired to coils at rows `posY+2` through
`posY+7`, exactly matching. Different author, different block type, from
`sayahali`'s single `TON` data point.

Unlike `sayahali`'s case, these coil rows contain no `shortCircuit`/`VLink`/
`FFBBlock` directly -- the block lives in its own separate row -- meaning
they were already being resolved by `parse_ladder_rungs` as ordinary
"pure series" rungs, just wrongly: a coil with no leading contact has
always been reported as unconditionally tied to the rail, with no check
for whether its leading wire instead originates at a known block's own
output edge. This is a real accuracy question about already-shipped
output, not a hypothetical -- so before writing anything, checked the
current corpus for rows with the identical shape (leading `emptyCell`,
zero contacts, then a coil) and found two, `Escalier_Mecanique.XEF` row 0
and `sayahali_conveyor_ali_conv.zef` rows 81/97 -- confirmed none of them
sit near any block's output-edge column, so they're genuinely
unconditional and needed to keep resolving exactly as before.

Implemented `_block_output_origins()` in `ladder.py`: precomputes, per
network, every `(row, column)` a block's output can originate a wire from,
scoped to exactly the evidenced case (`enEnO="true"`, declared outputs >=
declared inputs -- the corpus's `inputs > outputs` shapes, `ADD`/`SR`/
`INITCHART`/`SETSTEP`, still aren't attempted, same as before).
`parse_ladder_rungs` now checks every zero-contact coil row against it
before accepting "unconditional". A new model operation,
`LadderOperation.BLOCK_OUTPUT_REFERENCE`, represents a match -- `operand`
is `"{instance}.{pin}"` rather than a declared tag name, since the value
comes from another block's own output pin, not project data.

Re-ran the full real corpus after the change: the two genuinely-
unconditional cases above are byte-for-byte unaffected; no other real
fixture in the corpus happens to contain the "isolated coil row, matching
block nearby" shape at all (only `LD_1_Heating.xml`, local-only and thus
outside `parse_projects`' currently-recognized `LDExchangeFile` root, does
-- confirmed end to end by loading its `LDSource` node directly through
`parse_ladder_rungs`: five of its six real coils now resolve to
`block_output_reference`). Two new synthetic tests: one reproducing the
real fixed shape, one confirming a near-miss column (one off from the true
output edge) still resolves unconditional, unchanged.

Scoped deliberately narrow, and said so in the docstring: only a coil with
*zero* leading contacts in its own row. `LD_1_Heating.xml` itself has a
sixth row (`minus_5_percent`) with a real contact (`Start_process`) ahead
of the same block-output wire, separated from it by a genuine `emptyCell`
gap -- and it still resolves as `Start_process -> coil`, unchanged, exactly
as before this fix, because any row with a real contact in it was out of
scope. That surfaced a separate, deeper, not-yet-investigated question:
whether `parse_ladder_rungs`'s "every contact/coil in the row is one
series condition" reading has always been too permissive whenever a
genuine `emptyCell` gap sits between two real elements -- a pre-existing
question, not introduced by this change and not fixed by it either,
deliberately left alone rather than risk already-tested output on an
unrelated, unverified semantic under time pressure. 282 tests pass
(up from 280); Ruff and Pyright pass.

`emptyCell`-gap checkpoint (2026-09-25): the user had originally gone
looking for more SCADAPack evidence specifically hoping it would help
close remaining Control Expert ladder gaps; once that detour ran its
course, asked directly to come back and close this exact one, deferred at
the end of the block-output-fed-coil checkpoint above.

Checked the real risk before writing anything: scanned every tracked
fixture for a row with an `emptyCell` strictly between two cell-bearing
elements. Found exactly two, both in `sayahali_conveyor_ali_conv.zef`,
and both a different, already-correctly-diagnosed shape (two coils on one
row -- `ladder_series_unexpected_coil_position` already catches it
regardless of gap handling). Zero rows in the tracked corpus would change
behavior from this fix; the only known real-world case remains
`LD_1_Heating.xml` row 10 (local-only, no license, copied into
`reference/control-expert/` -- gitignored, confirmed never committed).

Implemented: `parse_ladder_rungs` now treats an `emptyCell` after at least
one contact has been seen as a genuine break -- starts a fresh segment,
discarding the disconnected one, instead of folding every contact in the
row into the coil's condition regardless of gaps. A leading run of
`emptyCell`/`HLink` before any contact is unaffected (that's the
already-confirmed "from the rail" case). First implementation reported
the discard the moment the gap was seen; the real-fixture test caught
that this fires prematurely on rows that are unresolved for *other*
reasons entirely (a `shortCircuit` elsewhere in the same row, or no coil
at all) -- `LD_1_Heating.xml` alone has several such rows, producing 5
diagnostics where only 1 (row 10's genuine case) was expected. Fixed by
deferring: the discard count is tracked through the row scan but only
reported once the row is confirmed to resolve as an actual rung.

Real corpus result: `LD_1_Heating.xml` row 10 (`Start_process` ahead of
`Heating_control`'s block-output wire feeding `minus_5_percent`) now
resolves identically to its five siblings -- `BLOCK_OUTPUT_REFERENCE`
naming `Heating_control.minus_5_percent`, then the coil -- instead of the
previous wrong `Start_process -> coil` reading, with the discarded
segment recorded via a new `ladder_disconnected_segment_discarded`
diagnostic rather than silently dropped. New real-fixture test calls
`parse_ladder_rungs` directly against the file's `LDSource` node (its
`LDExchangeFile` root is a per-section export shape this project's
capture pipeline doesn't otherwise recognize), confirming all six coil
rows and the exact discard count. Two new synthetic tests alongside it.
284 tests pass (up from 282); Ruff and Pyright pass.

`SR.Q1` re-check, no code change (2026-09-25): asked directly whether
`sayahali_conveyor_ali_conv.zef`'s `SR` instances already had the wired-
output evidence the `ADD`/`INITCHART`/`SETSTEP` backlog item needs.
Re-verified precisely rather than relying on the earlier summary: no --
every one of the five wired `SR` instances (`SR_2`/`3`/`4`/`5`/`7`) has
the identical shape (`shortCircuit(S1 landing) | HLink(1) | emptyCell(2)
| HLink(1) | coil`), and `Q1`'s own one-cell stub is separated from the
row's coil by that real gap -- genuinely disconnected, confirmed against
the now-shipped `emptyCell`-gap logic, same conclusion as before.

The question was still useful: it surfaced that the roadmap's
`inputs > outputs` backlog item had been lumping `SR` in with
`ADD`/`INITCHART`/`SETSTEP` as one open question, when it is actually
two. `SR` is `enEnO="false"`; the others are `enEnO="true"`. The "+1
padding row" ambiguity (a competing formula giving a different
prediction) is specifically an `enEnO="true"` question and does not
apply to `SR` at all. For `SR`, since hidden `EN`/`ENO` already compacts
the *input* side (`S1` confirmed at `posY+0`), the natural, untested
hypothesis is that the *output* side compacts the same way (`Q1` at
`posY+0`, not `posY+1`) -- a different question from the `ADD`-style one,
and one `_block_output_origins()` could not even detect yet regardless,
since it is gated to `enEnO="true"` blocks only. Roadmap split into these
two explicitly separate items so a future session (or this one) does not
re-conflate them.

Ladder SVG export, Milestone 1 (2026-09-25): shipped
`LadderSvgExporter` (`exporters/ladder_svg.py`), the first implementation
step of the new
[graphical diagram visualization roadmap](../roadmaps/graphical-diagram-visualization-roadmap.md).
Renders a `LadderRung`'s resolved series contacts/coils as standard
IEC 61131-3 symbols (open/closed contact, coil, set/reset coil markers),
`BLOCK_OUTPUT_REFERENCE` as a labeled dashed box, and any `LadderParallel`
branch as an explicit "not yet rendered" placeholder rather than silently
dropping it -- same never-guess posture as the rest of the parser. Output
is plain deterministic SVG text, the same `aoi_plantuml.py`-style
text-in/text-out contract, no raster/image-library dependency.

New CLI surface: `twinforge control-expert render <file> --output <dir>
[--routine NAME] [--network N]` (`cli/control_expert_render.py`), writing
one SVG file per `networkLD`. Building this surfaced a real model gap not
previously written down: `LadderRung` has no network-index field, and its
`number` (row) resets to 0 for every `networkLD` the parser walks, so nothing
in the model itself says which network a rung belongs to -- confirmed not
theoretical, since `Escalier_Mecanique.XEF` has a routine with multiple
`networkLD` siblings. Worked around at the CLI layer (not the model) by
grouping consecutive rungs that share the same parent
`SourceExtension.xml_path`, which is safe because the parser always emits
one network's rungs contiguously; documented in the roadmap as a real,
still-open modeling gap (`network_index` field) rather than treated as
solved.

Verified against the real corpus, not just synthetic rungs: rendering
`Escalier_Mecanique.XEF` end-to-end produced two correct SVGs (`Init_Logic`,
`Rising_Edge_Detection`) with the expected rung/operand structure; a third
`networkLD` in the same file produced no rungs at all (fully
`unresolved_ladder_row`), which the renderer correctly emits nothing for
rather than guessing. 8 new exporter tests plus 3 new CLI tests. 1501 tests
pass project-wide; Ruff and Pyright pass. Milestone 2 (unresolved-row and
inline `FFBBlock` rendering) and Milestone 3 (FBD) remain open.

Standalone DFB export (`.xdb`/`.XDB`) capture support (2026-09-25): user
supplied three more SCADAPack zips (`Realflo-Related DFBs v1.zip`,
`SCADAPack 47xi Lift Station Libraries.zip`, `SNMP_Polling_Zip_Files.zip`);
exploring them surfaced a real, well-scoped capture gap rather than a
parsing failure -- `capture_file`/`capture_bytes` never even looked at
`.xdb`/`.XDB` (suffix not in the recognized set), even though the content is
plain XML in the same DTD generation (`DTDVersion="41"`) as every XEF
fixture already supported, and its interior grammar (`FBSource`/
`FBProgram`/`STSource`/`FBDSource`/`inputParameters`/`outputParameters`/
`privateLocalVariables`) is *identical* to the already-mapped
project-embedded DFB case documented in
[the exchange capture spec](../architecture/control-expert-exchange-capture.md#standalone-dfb-export-xdbxdb-the-same-grammar-a-different-root-2026-09-25).

Fixed with a small, targeted change, not a parallel capture path: a new
`FB_EXCHANGE_SPEC` (root `FBExchangeFile`, genuinely a different document
shape from `FEFExchangeFile` -- no `program`/`logicConf`/`dataBlock` at
all -- so it is its own spec, not an alias entry like `ZEFExchangeFile`);
`capture_bytes`/`capture_file` now try a tuple of root specs
(`CONTROL_EXPERT_SPECS = (EXCHANGE_SPEC, FB_EXCHANGE_SPEC)`) instead of one,
a three-line change to `_inspect`'s root-matching, fully backward compatible
for every existing caller. Two new entry points,
`parse_function_block_library`/`parse_function_block_libraries`
(`parsers/control_expert/project.py`), reuse `_function_blocks`/
`_function_block_routine` completely unchanged -- zero new mapping code,
since that logic was already proven against 83 real project-embedded DFB
definitions. The `Controller` envelope these return is deliberately minimal
(name = the DFB's own `nameOfFBType`, everything else empty) rather than
pretending a standalone DFB has tags/hardware/programs it doesn't.

Verified against all 17 real `.xdb` files in
`reference/SCADAPack/Realflo-Related DFBs v1.zip` (gitignored, local-only --
not part of the committed test corpus): every one resolves to an
`AddOnInstruction` with populated parameters and routines, including the
`getregfloat5.xdb`/`GetRegFloatv6.XDB` pair (the same block, two real
versions, v2.00 and v2.04). `unresolved_type` diagnostics on locals typed as
another library block are expected -- a standalone DFB's `known_datatypes`
is empty by construction, same honest gap a project-embedded DFB has for a
type outside this project's own DDT/EFB catalog. 8 new synthetic tests
(`test_control_expert_function_block_library.py`) cover the capture root,
single- and multi-`FBProgram` bodies, FBD bodies through the shared
graphical parser, crypted bodies, a missing-`FBSource` diagnostic, root
rejection, and archive walking. 1509 tests pass project-wide; Ruff and
Pyright pass.
