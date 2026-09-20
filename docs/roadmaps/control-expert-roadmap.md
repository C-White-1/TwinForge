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
- [ ] Establish SFC adjacency/branch grammar before resolving complete connectivity

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
- [x] Order multi-block FBD networks from resolved shared-variable dataflow alone
- [x] Resolve simple declared-variable pin expressions case-insensitively
- [x] Classify supported lexical literals, unbound pins and unresolved expressions
- [x] Group shared-variable references without inventing graphical wires
- [x] Preserve ambiguous declarations instead of binding to the first occurrence
- [x] Capture and validate library block interfaces against actual calls
- [ ] Resolve indexed/member expressions using proven type definitions and bounds
- [ ] Interpret explicit FBD links/connectors with endpoint diagnostics
- [ ] Decode Ladder grid connectivity, branches and power-rail connections
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
uv run pytest tests/test_control_expert_sfc.py tests/test_control_expert_capture.py tests/test_control_expert_project.py tests/test_control_expert_graphical.py tests/test_graphical_bindings.py tests/test_cli_control_expert.py tests/test_model_json_export.py
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

Multi-block FBD order checkpoint: no local export contains an explicit
FBD link/connector element or a nonempty `execAfter` override, so that
grammar remains unimplemented pending evidence. The one real multi-block FBD
network (`readvar.zip`'s `ADDR`/`READ_VAR` pair) wires blocks purely through
already-resolved shared-variable dataflow; execution order now resolves from
that alone (`shared_variable_dataflow` basis), with self-reference handled,
multiple-writer groups reported `ambiguous_block_order`, and cycles, overrides,
unresolved pin bindings or any other unrelated diagnostic left unresolved.
The generic `unresolved_block_order` diagnostic moved from eager per-network
emission to a single centralized pass after order analysis runs, so it no
longer goes stale once a network resolves. 84 targeted tests passed; Ruff and
Pyright passed. Explicit FBD links/connectors, LD grid connectivity and
override-rule interpretation remain open.
