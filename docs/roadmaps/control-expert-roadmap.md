# Control Expert / Unity Pro import roadmap

Updated: 2026-09-23.

Objective: turn XEF/ZEF project evidence into useful vendor-neutral engineering
models while preserving all original content and explicitly reporting unresolved
semantics. Native re-import, compilation and runtime equivalence are separate
milestones, not consequences of successful XML parsing.

This roadmap owns delivery status and next work. The
[capture and mapping specification](../architecture/control-expert-exchange-capture.md)
owns observed structures, mapping decisions and evidence references. Update both
when capability changes; completed work below refers to the current working
tree, not a published release.

Safety scope: the reference corpus includes a real Control Expert M580
**safety** application, used here only as source evidence for the same
general-purpose capture, resolution and diagnostic work described below.
Parsing or modeling safety-program content is not safety validation, SIL
verification, certified translation, or any statement of suitability for a
safety function. A binding-kind like `declared_symbol` or a diagnostic like
`resolved` proves only that this project's own evidence standard was met --
never that the underlying logic is behaviorally correct, complete, or safe
to rely on. Anyone using TwinForge output from a safety project remains
solely responsible for their own safety assessment through the vendor's own
certified tools and process.

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
- [x] Specify periodic task timing from authoritative evidence -- see the
      task timing checkpoint below
- [x] Resolve timer-member expressions without simple-name assumptions (e.g.
      `Tempo1.Q`, a library TON instance's output parameter, in an SFC
      condition/action) -- see the sequential binding checkpoint below.
      Step-state (`.X`) in this same SFC condition/action context has no
      corpus evidence and stays unaddressed; a *different*, real, evidenced
      shape -- `.X` inside a full ST statement (`ELSIF G1_2.X THEN`) -- is
      now a separately scoped backlog item under ST analysis below, since it
      needs real expression parsing this project does not have yet
- [ ] Account for chart-control calls and multiple writers before execution claims
      (partial: chart-control call references now resolve -- see the chart
      control reference checkpoint below. Multiple writers for ordinary
      declared tags, across routines/sections rather than within one
      diagram, now resolve too -- see the coil write evidence checkpoint
      below. "Multiple writers" for chart/step state *specifically* --
      more than one `INITCHART`/`SETSTEP`/`FREEZECHART` call targeting the
      same chart or step -- was checked directly and has zero real corpus
      evidence: every apparent duplicate target across the whole reference
      corpus turned out to be the same project counted twice, once
      standalone and once as its own embedded export. Stays unimplemented
      on purpose, the same standard already applied to `parBranch`/
      `parJoint`, until a real fixture demonstrates the shape)
- [ ] Backlog: a chart-control call made *from ST*, not a graphical
      diagram -- real evidence: `FREEZECHART(G2, NOT Run_G2)` in
      `MultiGrafcet_Coordination_V1_2026.XEF`'s `FREEZE` program. The
      chart-control reference checkpoint's `_call_reference_kind` mechanism
      only ever looks at `GraphicalPin`/`GraphicalObject`, so this stays an
      `UnresolvedTagReference` (`identifier="G2"`) rather than a
      `StepStateReference`-style program reference. Found while measuring
      the tag dependency graph wiring checkpoint below; not attempted
      there, since it needs its own investigation (how the call-argument
      extraction for a regex-scanned ST call site should route into
      program-name resolution, not just member-suffix step-state matching)
- [x] Connect `analysis/tag_dependencies.py` (the shared machinery behind
      L5X cause-and-effect/alarm-candidate analysis) to Control Expert and
      CCW ladder logic -- see the structured ladder reference checkpoint
      below. It previously only read a routine's `LadderRung.text` (an RLL
      mnemonic string only the L5X converter populates); CE and CCW instead
      populate the portable, already-structured `LadderRung.network`, so
      their ladder logic was silently invisible to that whole analysis
      family. Only simple contact/coil read/write access is covered --
      matching what CE's own ladder capture ever resolves into `.network`
      in the first place (the pure-series case; see the Ladder series
      checkpoint)

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
      (`LibraryInterface.description` now also promotes Schneider's own
      `TypeDescriptiveForm` documentation text -- see the library
      description checkpoint below. Extensible-parameter matching now also
      recognizes a hidden `nin` parameter, not only the `(Extensible)`
      comment marker -- see the `nin` extensible parameter checkpoint below;
      real corpus coverage went from 0 to 20 previously-unresolved pins)
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
- [x] Determine an `FFBBlock`'s own grid column width, so row scanning need
      not abandon the rest of a row once it meets one; see the block-width
      checkpoint below. Confirmed constant (2 columns, independent of block
      type or pin count -- pin count instead grows row span, already
      resolved) across every real ladder network in the corpus.
- [x] Resolve a `shortCircuit`/`VLink` wire landing on an `enEnO="false"`
      block's own anchor row: `EN`/`ENO` are declared but never rendered,
      so the anchor row lands on the second declared input instead (`S1`
      for an `SR` block) -- confirmed against the vendor's own PDF
      rendering of a real `SR` block, and against a `shortCircuit` wrapping
      the block directly (`<shortCircuit><VLink/><FFBBlock/></shortCircuit>`,
      previously unrecognized and diagnosed as malformed). See the
      `enEnO="false"` landing checkpoint below. Real corpus result: all
      five wired `SR` instances in `sayahali_conveyor_ali_conv.zef` now
      resolve `S1` unconditionally; the two bare, unwrapped `SR_8`/`SR_9`
      correctly stay unresolved.
- [ ] Backlog: `R` (the second wireable input, one row below `S1`) is not
      resolved -- genuinely unwired in all five real `SR` instances checked,
      so there is no positive example to confirm the row-offset rule
      against. The output side remains unresolved too: a corpus-wide "fresh
      wire birth" scan found real, repeated (5/5, distinct targets each
      time) evidence that a block's output edge can originate a wire --
      `sayahali_conveyor_ali_conv.zef`'s five `TON` blocks each launch one
      at row `posY+2` into a `resetCoil`, and the user identified it as `Q`
      -- but the general row-to-pin rule for outputs still isn't fully
      pinned down from grid structure alone (the naive declaration-order
      reading gives `ET`, a `TIME` value that cannot legally drive a
      boolean coil; the "+1 padding row" explanation fits all evidence
      gathered so far but is confirmed only where competing formulas
      coincide -- `TON`, `SET`, `RESET`, `MBP_MSTR` -- not for the corpus's
      `n_in > n_out` shapes, `ADD`/`SR`/`INITCHART`/`SETSTEP`). Also,
      representing a block-to-block output reference needs a model
      addition (`LadderInstruction.operand` is a plain tag-name string
      today); not started. See the output-edge checkpoint below
- [x] Resolve multi-block/network order under link and override rules: explicit
      links are covered above; `execAfter` is now an extra dependency edge, an
      inference not vendor-documented -- see the `execAfter` checkpoint below
- [ ] Interpret section conditions, enable behavior and other control flow
      (partial: section `activationCondition`/`logicCondition` captured as
      lexical evidence -- see the section condition checkpoint below; `jumpSFC`
      connectivity is resolved -- see the `jumpSFC` checkpoint below; nothing
      is evaluated, and enable behavior remains open)
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

- [x] Promote a documented subset of scalar initial values with lexical provenance
      (BOOL/integer-family/REAL tag initializers promote -- see the scalar
      initial value checkpoint below; TIME stays lexical-only on purpose.
      Composite/array initial values -- struct members, array elements and
      DFB instance local-variable overrides -- now resolve their member/
      local identity and promote scalar leaves the same way -- see the
      composite initial value promotion checkpoint below; what stays
      unpromoted is the same kind of genuine, documented gap: TIME values,
      the still-open PID/regulation library and RIO-drop Device DDT
      families, library (EFB) instances with no captured internal
      structure, and catalog sub-structures not yet transcribed)
- [x] Model array lower bounds without zero-base loss, for DDT members
      (`DatatypeMember.dimension` retains the lexical `lower..upper` text
      unchanged, e.g. `"257..384"`, deliberately not renumbered from zero)
- [x] Capture DDT definitions and cross-references (`DDTSource`, including
      forward references between DDTs) and custom DFB definitions
      (`FBSource`/`FBProgram`, interface/locals/body -- see the DFB capture
      checkpoint below); device DDT remains a distinct, still-pending
      mechanism, not yet found in any local fixture
- [x] Distinguish library types, block-instance types and user-defined data types
      (see the type distinction checkpoint below)
- [ ] Extend ST analysis with source dialect/system-address evidence
      (partial: the shared `twinforge.structured_text` parser now supports
      Control Expert's own labeled-statement/`JMP` GOTO-style control flow
      -- see the label/jump statement checkpoint below -- and a
      `%`-prefixed direct/system address inside an ST expression (`%S18`,
      `%SW12`) -- see the direct-address expression checkpoint below.
      Unsupported statements in the corpus are now 71, down from an
      original 271. A digit-led KKS-style identifier (`00CMA01EA900`, real
      evidence, an industrial tag-naming convention) is no longer
      mis-tokenized as a numeric literal either -- see the digit-led
      identifier checkpoint below; 42 distinct real names across the
      corpus now resolve as names)
- [x] Step-state (`.X`) reference used inside a full ST statement, not just
      as an isolated LD contact operand or SFC condition/action variable --
      real evidence: `ELSIF G1_2.X THEN` in
      `MultiGrafcet_Coordination_V1_2026.XEF`. The investigation this note
      asked for is done: `twinforge.structured_text` (built for L5X/Logix
      ST) does generalize to Control Expert's own ST -- see the label/jump
      statement checkpoint, which found and closed the dominant real gap
      (57% of unsupported statements). `.X` itself now resolves too -- see
      the ST step-state reference checkpoint below -- via
      `analysis/tag_dependencies.py` (an optional, opt-in parameter; an
      L5X caller offering no step evidence sees no behavior change), now
      also called from `parse_project` itself and exposed as
      `tag_dependency_graph` in CLI JSON -- see the tag dependency graph
      wiring checkpoint below
- [ ] Add SFC, IL/LL984 and additional task/hardware forms as evidence becomes available
- [ ] Add populated DTM and modern M580/Control Expert examples (a real,
      populated Control Expert V14.0 M580 **safety** project is now in the
      corpus -- see the explicit FBD link and power supply checkpoints above
      -- but its `DTMConfiguration` content specifically has not been surveyed)
- [x] Characterize encrypted/protected exports and retain unsupported content
      (`FBSource/crypted`, 7 real occurrences; see the encrypted body
      checkpoint below for what "characterize" means here and why the full
      blob is not duplicated into the neutral model)

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

The last full run of the command's test set passed 280 tests, including optional
local samples; Ruff and Pyright passed. This is a dated development checkpoint,
not a substitute for running the checks after future changes.

The complete, dated history of every checkpoint -- what was measured, what
real corpus evidence justified each change, and exact test/lint/type-check
results at the time -- is kept separately in the
[development checkpoint journal](../development/control-expert-checkpoints.md).

For each milestone, record code, independent tests, source evidence, open
limitations and user-facing documentation together. Do not mark graphical
execution or vendor compatibility complete based only on successful capture.
