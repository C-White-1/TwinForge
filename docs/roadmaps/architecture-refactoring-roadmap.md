# Architecture and refactoring roadmap

This document tracks TwinForge's responsibility boundaries and structural
maintenance. The main roadmap tracks engineering capabilities; this roadmap
tracks whether those capabilities remain independently testable, vendor
neutral where appropriate, and safe to extend.

## Status definitions

- **Complete** means the responsibility has a named boundary, focused tests,
  and no known reverse dependency.
- **Established** means the boundary is in active use but may still contain
  more than one internal responsibility.
- **Next** identifies an evidence-backed refactor, not a speculative rewrite.
- **Deferred** means more implementations or target evidence are needed before
  selecting a stable abstraction.

Refactoring must preserve source data and observable behavior. A smaller file
is not, by itself, evidence of improved architecture.

## Dependency direction

```text
schema and specifications
          |
          v
lossless capture and parsers
          |
          v
source converters and resolution
          |
          v
vendor-neutral model
          |
          +--> analysis
          +--> executable IR and runtime contracts
          |
          v
generic exporters
          |
          v
target adapters and deployment packaging
```

Required rules:

1. Model objects do not import exporters or target packages.
2. Exporters consume resolved model or IR objects; they do not parse L5X.
3. CODESYS, OpenPLC, and other runtime APIs stay outside the neutral model.
4. Pydantic validates untrusted boundary data; internal model and IR objects
   remain ordinary typed dataclasses unless runtime validation is required.
5. Unknown source content and source extensions survive every refactor.
6. Public façades remain stable while internal responsibilities move.

## Completed responsibility separations

### L5X module conversion — complete

The former module converter was divided into:

- `module_identity.py` for identity, slot, catalog, vendor, and keying facts;
- `module_engineering.py` for units and range evidence;
- `module_capability.py` for capacity and channel capability;
- `conversion_value.py` for safe typed source-value conversion; and
- `module.py` as the orchestration façade.

Evidence:

- module converter and electronic-key tests;
- Pyright-clean constructor and optional-value handling; and
- commit `66388e5`.

### AutomationML export — complete

AutomationML responsibilities are separated into:

- instance hierarchy;
- class-library generation;
- signal and I/O generation;
- deterministic identity;
- CAEX XSD validation;
- semantic and external-reference validation;
- shared element and type helpers; and
- `AutomationMLExporter` as the public façade.

Evidence:

- component-level exporter tests;
- CAEX and semantic-reference validation tests;
- successful AutomationML Editor loading; and
- commit `66388e5`.

### PLCopen foundation — established

The first PLCopen refactor separated:

- generic XML and qualified-name helpers;
- common PLCopen types and profiles;
- RLL parsing structures;
- CODESYS profile metadata;
- XSD validation; and
- the public `PLCopenExporter`.

This boundary enabled CODESYS-specific behavior without putting it in the
vendor-neutral model. The main exporter has since grown as instruction and
operand support expanded, so the foundation is established but the internal
emission responsibilities need another pass.

Evidence:

- standard and CODESYS profile tests;
- standard XSD validation;
- successful CODESYS imports and builds; and
- commit `66388e5`.

### Executable Structured Text and AOI pipeline — established

Lossless syntax, semantic analysis, executable IR, normalization, lifecycle
roles, canonical IEC emission, and CODESYS adaptation are separate stages.
`Str_Capacity` and `RTC_PulseGen` prove the pipeline without AOI-name special
cases.

Evidence:

- structured-text parser and semantic tests;
- IR execution and normalization tests;
- AOI lifecycle tests;
- CODESYS import, build, and online RTC observation; and
- commits `0b2fb01`, `4af93c6`, and `a3ef865`.

### CODESYS target boundary — established

Target-specific runtime and deployment behavior now lives under
`twinforge.targets.codesys`. It includes:

- normalized EtherNet/IP module services;
- native diagnostic and reconfiguration evidence;
- Pydantic deployment-manifest validation;
- native-template semantic checks; and
- reproducible deployment bundle packaging.

The reusable PowerFlex behavior and module-service contracts remain separate
from native CODESYS device-tree configuration.

Evidence:

- native CODESYS exports 33, 44, 45, and 46;
- one-drive and two-drive successful builds;
- clean two-stage native-device and PLCopen import;
- deployment bundle tests; and
- commits `89db592` through `829f747`.

### Type checking and CI — complete

Pyright checks maintained source, tests, and examples. Ruff and the full test
suite run in the quality workflow on supported operating systems.

Evidence:

- `.github/workflows/quality.yml`;
- `[tool.pyright]` in `pyproject.toml`; and
- zero-error local and GitHub workflow runs.

## Active refactoring backlog

### Priority 1: split the general PLCopen exporter

`exporters/plcopen.py` again contains several distinct responsibilities:

- controller/project traversal;
- variable and initial-value emission;
- rung graph construction;
- instruction-specific block emission;
- operand normalization and surrogate generation;
- timer and one-shot discovery; and
- diagnostic collection.

Next:

- [x] Extract controller/project structure orchestration
- [x] Extract variable and datatype emission
- [x] Move instruction emitters behind a registry or focused collaborators
- [x] Extract operand preparation and surrogate-symbol management
- [x] Keep `PLCopenExporter` as the stable façade
- [x] Preserve deterministic IDs and diagnostic ordering
- [x] Prove byte-stable output for existing fixtures where timestamps are
  fixed

This is the highest-value next refactor because every new RLL instruction
currently increases pressure on the same class.

Operand discovery, IEC-safe surrogate generation, comparison temporaries,
timer state and one-shot state are now prepared by
`exporters.plcopen_operands.PLCopenOperandPlanner`. The serializer consumes
its immutable plan and retains the existing public exporter API. Fixed-time
standard and CODESYS fixture hashes protect serialization stability, while
focused planner tests protect symbol and diagnostic ordering.

Variable filtering, scalar and derived type declarations, initial values,
source-evidence extensions, engineering-unit evidence and documentation are
now owned by `exporters.plcopen_variables.PLCopenVariableEmitter`. Target
timer naming remains an injected policy, keeping this emitter reusable by
future target profiles.

Project headers, PLCopen document scaffolding, standard program/task traversal
and controller resource construction are now owned by
`exporters.plcopen_project.PLCopenProjectOrchestrator`. Target application
wrapping is supplied as an optional callback, so CODESYS project metadata
remains isolated in its existing adapter.

Executable condition and output opcodes now pass through
`exporters.plcopen_instructions.PLCopenInstructionRegistry`. Typed instruction
requests carry graph inputs and prepared auxiliary state, while output
emissions return explicit continuation state. This separates opcode dispatch
from rung graph ordering without changing existing emitter implementations or
local-ID allocation.

### Priority 2: separate CODESYS IR project serialization

`exporters/codesys_plcopen_ir.py` currently combines:

- integration configuration objects;
- program and task generation;
- POU/interface serialization;
- generic-array encoding;
- lifecycle-method serialization;
- project-structure metadata; and
- target-library metadata.

Next:

- [x] Move integration dataclasses and naming rules into a focused module
- [x] Separate POU/interface serialization from project/task structure
- [x] Separate lifecycle-method generation
- [x] Separate required-library discovery and metadata emission
- [x] Keep `CodesysIRPLCopenExporter` as the stable façade
- [x] Preserve import-tested XML structure and deterministic object IDs

Integration bindings, generated program variables, multi-call configuration,
task defaults, binding-name policy and captured-default translation now live
in `exporters.codesys_ir_integration`. The public exporter package and the
former `codesys_plcopen_ir` import path retain compatibility re-exports.

Reusable-unit POU structure, interface direction groups, local declarations,
generic-array evidence and IEC datatype encoding now live in
`exporters.codesys_ir_pou`. Lifecycle emission and deterministic identity are
injected callbacks, keeping method generation and project metadata outside
the POU serializer.

Prescan eligibility, native `FB_Init` method serialization and lifecycle
method identity now live in `exporters.codesys_ir_lifecycle`. The exporter
uses the same collaborator for diagnostic mapping, POU method emission and
project-tree membership, preventing those three views from drifting.

Wall-clock runtime type discovery, proven CODESYS library definitions,
Library Manager identity and navigator membership now live in
`exporters.codesys_ir_libraries`. Resource metadata and project structure use
the same requirement policy.

Priority 2 is complete. The package-level and module-level exporter symbols
remain the same façade. Fixed-time hashes for ordinary AOI, lifecycle-method
and wall-clock-library documents now enforce byte-stable XML and deterministic
object IDs alongside the existing CODESYS import-tested fixtures.

### Priority 3: move PowerFlex CODESYS composition into the target package

`exporters/powerflex525_iec.py` contains both the neutral PowerFlex IEC unit
and CODESYS project composition helpers.

Next:

- [x] Retain neutral PowerFlex IR construction in the exporter or a neutral
  profile module
- [x] Move `PowerFlex525CodesysDevice` and CODESYS integration builders under
  `targets.codesys`
- [x] Keep compatibility re-exports while callers migrate
- [x] Confirm the neutral unit has no CODESYS imports
- [x] Preserve single-drive and multi-drive generated output

Priority 3 is complete. Neutral PowerFlex executable construction now lives
in `exporters.powerflex525_core`; CODESYS device descriptors and application
composition live in `targets.codesys.powerflex525`. Package-level and former
`exporters.powerflex525_iec` imports remain compatibility aliases. An AST
boundary test prevents CODESYS dependencies from returning to the neutral
core, and fixed-time hashes protect single- and multi-drive documents.

### Priority 4: split deployment packaging after a second profile

The current CODESYS deployment module deliberately keeps manifest validation,
native-template checks, instructions, and packaging together while only one
device profile is proven.

Deferred until another device profile or target exists:

- [ ] Separate generic CODESYS bundle packaging from PowerFlex fields
- [ ] Introduce reusable EtherNet/IP connection-manifest types
- [ ] Add profile-specific native evidence validators
- [ ] Avoid abstract base classes until two real implementations establish
  the common behavior

### Priority 5: split native OpenPLC project generation

`targets/openplc/native_project.py` grew from a deliberately small format
probe into the implementation boundary for project files, declarations,
location validation, ladder graphs, timer lowering, retained timers, shared
counters, telemetry, and deterministic identities. At more than 2,000 lines,
it now has multiple independently evidenced reasons to change. The counter
source-shape matcher is already separated in `targets/openplc/counter.py`,
which establishes a practical extraction seam.

Next:

- [x] Keep `OpenPLCNativeProjectExporter` and its result/error types as the
  stable public façade
- [x] Extract project, device, pin-mapping, and POU document packaging
- [x] Extract located-address and telemetry-request validation
- [x] Extract variable and compatibility-block declarations
- [x] Extract deterministic native graph identities and low-level node/edge
  serialization
- [x] Move ordinary contact, coil, serial, parallel, and seal-in lowering
  behind a focused ladder-graph collaborator
- [x] Move TON/TOF/RTO lowering and elapsed-time telemetry behind a timer
  collaborator
- [x] Complete the existing counter boundary by moving `TF_COUNTER` graph
  emission, telemetry, and compatibility-block source beside counter matching
- [x] Preserve fail-fast unsupported-semantics diagnostics and their ordering
- [x] Preserve byte-stable generated fixtures and the runtime-validated
  project-directory schema
- [x] Avoid a generic instruction-plugin abstraction until a second lowering
  family demonstrates the required interface

This refactor is now evidence-backed rather than speculative: timer and
counter support have changed the same module independently, and their native
graph construction can be tested without changing project packaging. It
should precede broad additions such as comparisons, arithmetic, moves, and
one-shots.

The first slice moved the runtime-verified project scheduling envelope,
device configuration, empty pin map, deterministic JSON formatting, document
writing, and required POU-directory creation into
`targets.openplc.native_packaging`. Existing integration and determinism tests
continue to exercise the stable exporter façade and generated file set.

The second slice moved local Boolean locations, timer elapsed telemetry,
counter accumulator telemetry, and counter status telemetry validation into
`targets.openplc.native_validation`. The shared unsupported-semantics exception
now lives in `targets.openplc.native_errors` while remaining available from
the original public import paths. Existing diagnostic tests protect message
text and ordering.

The third slice moved native local-variable declarations, COUNTER discovery,
required compatibility-block selection, and the byte-stable compatibility
sources into `targets.openplc.native_declarations`. The later counter boundary
became the semantic owner of `TF_COUNTER`; declaration packaging consumes that
source without depending on the exporter façade. `TF_RTO` remains with the
declaration boundary pending evidence that another timer implementation needs
the same separation.

The fourth slice moved deterministic UUID and numeric identifiers plus shared
connector, rail, contact, coil, parallel-node, and edge serialization into
`targets.openplc.native_graph`. Instruction-specific block geometry remains
with timer, counter, and conversion lowering until those collaborators move;
the graph module therefore contains only primitives shared by independent
lowering families.

The fifth slice moved ordinary serial contact chains, coils, two-path parallel
branches, optional XIO stop tails, and seal-in graph geometry into
`targets.openplc.native_ladder`. The façade still validates source shapes and
dispatches timer and counter groups before ordinary Boolean rungs, preserving
diagnostic and source-order behavior.

The sixth slice moved function-block interface variables and connectors plus
connected input/output variable nodes into `targets.openplc.native_blocks`.
This shared primitive boundary lets timer and counter collaborators depend on
graph serialization directly instead of importing private helpers from the
exporter façade.

The seventh slice established `targets.openplc.native_timer` as the owner of
canonical TON/TOF plus RTO/DN/RES source-group recognition and timer instance
type discovery. Timer graph emission and elapsed-time telemetry remain in the
façade until the next slice, so the timer-lowering checklist item remains
open rather than overstating completion.

The eighth slice completed that boundary by moving TON/TOF timer blocks, RTO
wrapper graphs, preset nodes, and runtime-verified TIME-to-DINT elapsed
telemetry into `targets.openplc.native_timer`. The façade now only asks the
collaborator to recognize and lower timer groups, while byte-stable fixture
tests continue to protect the native graph representation.

The ninth slice completed the counter boundary in
`targets.openplc.counter`. Canonical CTU/CTD recognition, duplicate-state
diagnostics, shared-state graph emission, accumulator and OV/UN telemetry,
and the byte-stable `TF_COUNTER` Structured Text source now have one semantic
owner. The façade retains only ordered dispatch and project assembly.

The tenth slice completed the façade boundary. Entrypoint selection and
fail-fast source admission now live in `targets.openplc.native_semantics`,
while ordered declaration and rung assembly live in
`targets.openplc.native_program`. `native_project.py` retains the stable public
exporter/result API and coordinates planning, validation, packaging, and
writing. The full regression suite protects diagnostic ordering and the
byte-stable runtime-validated project schema; no speculative instruction
plugin abstraction was introduced.

Priority 5 is complete. The original 2,032-line implementation is now a
114-line public façade over focused packaging, validation, declaration,
semantic-admission, graph, ladder, timer, counter, and program-assembly
modules. Further extraction is not warranted without a new independent reason
to change one of those responsibilities.

### Priority 6: improve repository navigation and artifact boundaries

TwinForge is not currently too large as a Git repository. The August 2026
baseline is approximately 674 tracked files and 11.5 MiB. Its maintainability
risk is conceptual breadth: parsing, neutral modelling, analysis, PLCopen XML,
CODESYS, OpenPLC, AutomationML, device knowledge, reports, and experiments are
all legitimate parts of the toolkit, but their relationships are not yet
obvious to a new contributor.

The objective is to make the existing architecture discoverable before
considering additional repositories or package splits. This work must not
move functioning code merely to make the directory tree look smaller.

Planned sequence:

- [x] Add authoritative PlantUML sources under
  `docs/architecture/diagrams/` for the end-to-end conversion pipeline,
  target-specific output paths, and the native OpenPLC façade/collaborators
- [x] Add `docs/README.md` as the documentation landing page, covering getting
  started, architecture, capabilities, target guides, experiments, roadmaps,
  and reference provenance
- [x] Add a concise repository and package-responsibility map to
  `ARCHITECTURE.md`, including explicit ownership and prohibited dependencies
- [x] Document an artifact policy for product source, tests, executable
  examples, external reference material, curated reports, generated output,
  and temporary files
- [ ] Add a cross-target capability matrix covering parse, model, generic
  PLCopen XML, CODESYS, native OpenPLC, and AutomationML support
- [ ] Review tracked `examples/` and `reports/` content against the artifact
  policy without deleting evidence or moving licensed material into Git
- [ ] Consolidate disposable test output beneath one ignored location, or use
  pytest-managed temporary directories, while preserving failure artifacts
  needed for diagnosis
- [ ] Reassess repository splitting only if independent release cycles,
  incompatible dependencies, or materially separate contributor groups emerge

Acceptance criteria:

- A new contributor can identify the shared pipeline and target branch points
  from the documentation index and diagrams.
- Every top-level artifact category has a documented purpose and tracking
  policy.
- Generated and temporary content cannot be mistaken for authoritative source
  or curated evidence.
- The capability matrix distinguishes implemented, partially supported,
  evidence-gated, and unsupported behavior.
- No source-data preservation, public import, fixture, or generated-output
  behavior changes as a consequence of this organizational work.

## Ongoing architecture work

- [x] Add dependency-direction tests if accidental reverse imports become a
  recurring problem
- [x] Review public `__init__` re-exports as APIs grow
- [x] Stop tracking generated `*.egg-info` metadata in a dedicated cleanup
  commit
- [x] Add an OpenPLC target without importing CODESYS assumptions
- [x] Determine whether the observed OpenPLC editor exposes PLCopen XML import
- [x] Validate a generated native OpenPLC project through editor load, build,
  and runtime smoke tests
- [x] Add a deterministic OpenPLC smoke fixture workflow and native validation
  checklist
- [x] Add native OpenPLC project-directory packaging after ladder source
  evidence establishes the `.ld` JSON schema
- [x] Validate native OpenPLC serial, parallel, seal-in, and canonical `TON`
  lowering through editor, compiler, and runtime tests
- [x] Expose optional `TON.ET` telemetry through an explicitly configured
  `%MD` location and the runtime-verified `TIME_TO_DINT` conversion
- [x] Capture native OpenPLC `TOF` editor output and validate immediate-on,
  delayed-off, and cancellation behavior at runtime
- [x] Implement canonical Rockwell `TOF`/`.DN` lowering with a distinct IEC
  `TOF` declaration and block type
- [x] Validate the TwinForge-generated `TOF` fixture through OpenPLC compile
  and runtime behavior tests
- [x] Establish retained accumulator, enable, timing, done, pause/resume, and
  reset semantics for Rockwell `RTO`/`RES`
- [x] Implement the evidenced adjacent `RTO`/`.DN`/`RES` pattern through the
  generated OpenPLC `TF_RTO` compatibility function block
- [x] Compile and runtime-test the TwinForge-generated `RTO/RES` fixture
- [x] Establish that native OpenPLC `CTU_DINT` saturates at its preset while
  Rockwell `CTU.ACC` continues counting
- [x] Implement canonical Rockwell `CTU`/`.DN`/`RES` lowering through the
  generated counter compatibility function block with optional `%MD`
  accumulator telemetry
- [x] Compile and runtime-test the independently generated CTU project,
  including rising-edge accumulation, done state, continued counting, reset,
  and count-enable behavior
- [x] Capture and runtime-test native OpenPLC `CTD_DINT`; confirm that it
  saturates at zero and is not a faithful Rockwell `CTD` replacement
- [x] Design shared Rockwell `COUNTER` state for paired CTU/CTD use, including
  `.ACC`, `.PRE`, `.DN`, `.OV`, `.UN`, source scan order, initial accumulator
  evidence, and `RES`
- [x] Specify the shared counter state, execution rules, evidence boundary,
  and initial supported source shapes in
  `docs/architecture/counter-execution.md`
- [x] Implement canonical standalone CTD and paired CTU/CTD lowering through
  one generated `TF_COUNTER` state owner
- [x] Compile and runtime-test the generated paired `TF_COUNTER` OpenPLC
  fixture, including initialization, both count directions, done state,
  continued counting, negative accumulation, and reset
- [x] Runtime-test simultaneous CTU/CTD rising edges with a deterministic
  in-program stimulus so source-order behavior is exercised within one scan
- [x] Runtime-test `TF_COUNTER` signed-DINT overflow and underflow rollover,
  including the independent `OV` and `UN` status latches
- [x] Consolidate CTU-only, CTD-only, and paired CTU/CTD lowering onto the
  single proven `TF_COUNTER` state owner
- [x] Recompile and runtime-test the regenerated CTU-only project after
  retiring the duplicate `TF_CTU` implementation
- [ ] Revisit physical channel and CIP assembly entities when EDS or live
  evidence supports them
- [ ] Review this document whenever a module gains a second independent
  reason to change

Generated `src/twinforge.egg-info` metadata is no longer tracked.
`*.egg-info/` was already ignored; authoritative package configuration remains
in `pyproject.toml` and the resolved development environment remains in
`uv.lock`.

The PowerFlex target relocation exposed a real reverse-import cycle, meeting
the threshold for dependency tests. AST checks now protect neutral `model`
and `ir` layers and restrict exporter-to-target imports to the documented
package façade and legacy compatibility shim. Public exporter and CODESYS
target `__all__` surfaces are checked for duplicate or unresolved names.

`targets.openplc.OpenPLCExporter` now provides a minimal standards-based
target façade over PLCopen XML 2.01. It emits no CODESYS extensions and is
byte-identical to the generic standard profile. The observed OpenPLC editor
offers PLCopen XML and CODESYS XML export but no corresponding import
operation, so this is an exchange/comparison artifact rather than a native
project loader.

The native validation workflow is documented in
`docs/experiments/OpenPLC-native-project-compatibility.md`. It deliberately
starts with a two-tag, one-rung deterministic fixture before testing a
representative L5X conversion, so target compatibility can be distinguished
from instruction coverage.

Native OpenPLC evidence established that its working-project format is a
directory containing scheduling metadata, language-specific POU files, device
configuration, and pin mappings. The Ladder Diagram `.ld` file uses an IEC
declaration envelope around an OpenPLC JSON rung model. A separate native
packager now implements the evidenced local-BOOL serial and two-path parallel
subset, seal-in branches; canonical Rockwell `TON`, `TOF`, and `RTO`
lowering; and standalone or paired `CTU`/`CTD` lowering through one shared
`TF_COUNTER` state owner. Optional `TON` elapsed-time telemetry is exposed
through a located `%MD` `DINT`. Counter telemetry can expose the accumulator
and the independent overflow and underflow latches through explicitly
configured locations. The packager uses deterministic identities and
fail-fast rejection of unsupported semantics. Generated fixtures have opened,
compiled, uploaded, and passed runtime truth-table, seal-in, timer,
retained-timer, counter, simultaneous-edge, overflow, and underflow tests on
OpenPLC Runtime v3. The packager remains separate from the generic PLCopen
exporter.

## Refactor completion checklist

A refactor is complete only when:

- [ ] behavior and lossless source preservation remain covered by tests;
- [ ] Ruff, Pyright, and the full test suite pass;
- [ ] dependency direction follows the architecture above;
- [ ] target-specific types have not entered the neutral model or IR;
- [ ] public imports remain compatible or have a documented migration;
- [ ] generated artifacts remain semantically equivalent;
- [ ] relevant architecture and capability documents are updated; and
- [ ] this roadmap records the completed item and any new follow-up work.

## Tracking convention

Every architecture-oriented commit should update this roadmap in the same
change. Capability roadmaps may link here rather than duplicating structural
tasks. Commit messages should identify the responsibility moved, for example:

```text
Refactor PLCopen operand preparation
```

Avoid generic messages such as `refactored`; they make later audits
unnecessarily dependent on diff archaeology.
