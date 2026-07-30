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

- [ ] Extract controller/project structure orchestration
- [x] Extract variable and datatype emission
- [ ] Move instruction emitters behind a registry or focused collaborators
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

- [ ] Move integration dataclasses and naming rules into a focused module
- [ ] Separate POU/interface serialization from project/task structure
- [ ] Separate lifecycle-method generation
- [ ] Separate required-library discovery and metadata emission
- [ ] Keep `CodesysIRPLCopenExporter` as the stable façade
- [ ] Preserve import-tested XML structure and deterministic object IDs

### Priority 3: move PowerFlex CODESYS composition into the target package

`exporters/powerflex525_iec.py` contains both the neutral PowerFlex IEC unit
and CODESYS project composition helpers.

Next:

- [ ] Retain neutral PowerFlex IR construction in the exporter or a neutral
  profile module
- [ ] Move `PowerFlex525CodesysDevice` and CODESYS integration builders under
  `targets.codesys`
- [ ] Keep compatibility re-exports while callers migrate
- [ ] Confirm the neutral unit has no CODESYS imports
- [ ] Preserve single-drive and multi-drive generated output

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

## Ongoing architecture work

- [ ] Add dependency-direction tests if accidental reverse imports become a
  recurring problem
- [ ] Review public `__init__` re-exports as APIs grow
- [ ] Stop tracking generated `*.egg-info` metadata in a dedicated cleanup
  commit
- [ ] Add an OpenPLC target without importing CODESYS assumptions
- [ ] Revisit physical channel and CIP assembly entities when EDS or live
  evidence supports them
- [ ] Review this document whenever a module gains a second independent
  reason to change

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
