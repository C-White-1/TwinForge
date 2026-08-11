# Architecture

TwinForge separates source-specific capture from its vendor-neutral model and
output formats.

## Architecture diagrams

### End-to-end conversion pipeline

![TwinForge conversion pipeline](docs/architecture/diagrams/twinforge_conversion_pipeline.svg)

[PlantUML source](docs/architecture/diagrams/conversion-pipeline.puml)

### Target-specific output paths

![TwinForge target output paths](docs/architecture/diagrams/twinforge_target_output_paths.svg)

[PlantUML source](docs/architecture/diagrams/target-output-paths.puml)

### Native OpenPLC façade and collaborators

![Native OpenPLC façade and collaborators](docs/architecture/diagrams/twinforge_openplc_native_facade.svg)

[PlantUML source](docs/architecture/diagrams/openplc-native-facade.puml)

The `.puml` sources are authoritative. The adjacent SVG files are tracked so
GitHub can render the diagrams without a PlantUML service or browser plugin.
The diagrams describe responsibility and data-flow boundaries rather than a
fixed feature inventory. CODESYS conversion is validated for both Structured
Text and Ladder Diagram, while instruction and function coverage continues to
expand through evidence-backed implementation and testing.

```text
L5X specification tables
        ↓
generic XML capture
        ↓
CapturedSection
        ↓
L5X converters
        ↓
Plant / Controller domain model
        ↓
analysis and enrichment
        ↓
PLCopen XML | AutomationML | reports
```

## Repository responsibilities

| Path | Ownership and tracking policy |
| --- | --- |
| `src/twinforge/` | Installable product source and public Python APIs |
| `tests/` | Automated unit, integration, regression, and architecture tests |
| `docs/` | Maintained guides, architecture, experiments, and roadmaps |
| `examples/` | Thin CLI wrappers and focused executable demonstrations |
| `scripts/` | Maintainer utilities, not public library APIs |
| `reports/` | Curated engineering evidence and reviewed report artifacts |
| `reference/` | Ignored local standards, schemas, manuals, and evidence |
| `.github/` | Repository automation and CI workflow definitions |
| `build/` | Generated packaging output; never authoritative source |
| `.pytest-*`, caches, and virtual environments | Disposable local state |

Externally sourced material belongs under the ignored `reference/` tree unless
its provenance and redistribution rights explicitly permit tracking. Generated
output does not become authoritative merely because it resembles a source or
fixture. The detailed artifact policy remains a separate roadmap item.

## Package responsibilities

- `schema.l5x`: declarative L5X elements, attributes, applicability, and
  requiredness.
- `parsers.l5x`: lossless XML capture and the document parsing façade.
- `converters.l5x`: L5X conversion, enrichment, and reference resolution.
- `model`: vendor-neutral domain objects, relationships, and provenance.
- `analysis`: read-only coverage, dependency, portability, and report data.
- `structured_text`: lossless ST tokens, syntax, parsing, and semantics.
- `ir`: typed vendor-neutral executable representation and normalization.
- `runtime`: target-neutral runtime contracts and reference behavior.
- `exporters`: generic IEC, PLCopen XML, AutomationML, and report output.
- `targets.codesys`: CODESYS adaptation, evidence, and deployment packages.
- `targets.openplc`: standards façade and native OpenPLC project generation.
- `assembly`: cross-document, device, communication, and promotion assembly.
- `discovery`: bounded capture, acceptance, reconciliation, and lifecycle.
- `transport`: authorized protocol transports and session boundaries.
- `cli`: user orchestration, diagnostics, exit codes, and filesystem actions.
- `knowledge`: curated device and protocol facts with explicit evidence scope.
- `datatypes`: reusable protocol scalar and reference value types.
- `core`: small shared configuration, exception, logging, and utilities.
- `services`: earlier application-service experiments; not a preferred owner
  for new logic.
- `graph`: earlier graph models; new graphs use established analysis and
  assembly boundaries.
- `plugins`, `protocols`, and `samples`: reserved or early-stage namespaces
  without stable public contracts.

The final three entries identify present repository state, not desired dependency
centres. New work should use the established model, analysis, assembly,
transport, exporter, and target boundaries unless a documented refactor proves
a better owner.

## Dependency rules

Dependencies flow from source capture toward the neutral model and then toward
analysis, serialization, target adaptation, or application orchestration.

- `model` may consume other neutral model and value types. It must not consume
  parsers, converters, exporters, discovery transports, or targets.
- `ir` may consume neutral model, value, and syntax contracts. It must not
  consume exporters or target packages.
- `schema.l5x` may consume declarative schema helpers. It must not perform
  model conversion or consume exporters or targets.
- `converters.l5x` may consume captured source, schema, and the neutral model.
  It must not consume exporters or target adapters.
- `analysis` may consume the neutral model, syntax, IR, and analysis results.
  It must not own filesystem-writing CLI or target deployment behavior.
- Generic `exporters` may consume resolved model, analysis, and IR. They must
  not parse source XML or depend on undocumented target APIs.
- `targets.*` may consume neutral contracts and generic emission services.
  One target must not own assumptions belonging to another target.
- `transport` and `discovery` may consume protocol contracts and explicit
  authorization policy. They must not silently mutate accepted core models.
- `cli` may consume public application façades. It must not hide semantic
  rules that cannot be independently tested below the CLI.

Explicit compatibility shims are exceptions only when documented and protected
by architecture tests. They are migration surfaces, not permission to reverse
the general dependency direction.

PLCopen export is divided into target-neutral types, RLL parsing, XML/value
helpers and validation, project orchestration, plus target adapters. A
pre-serialization operand planner discovers portable symbols, comparison
temporaries, timers and one-shots without constructing XML. A separate
variable emitter serializes supported tag types, initial values and retained
source evidence with the target timer type supplied as policy. Generic
project scaffolding and controller traversal delegate target application
wrapping through an injected callback. Typed instruction dispatch separates
opcode-to-emitter selection from rung graph ordering and carries explicit
block-continuation state. CODESYS project structure and extensions are
isolated in `exporters.plcopen_codesys`; a future OpenPLC adapter should
consume the same neutral conversion and emission services.

AutomationML export is divided into instance-hierarchy construction,
class-library generation, signal/I/O generation, deterministic identity, CAEX
XSD validation and semantic-reference validation. `AutomationMLExporter`
remains the serialization and filesystem façade.

Architecture status, active hotspots, dependency rules and refactor completion
criteria are maintained in the
[architecture and refactoring roadmap](docs/roadmaps/architecture-refactoring-roadmap.md).
The general PLCopen and CODESYS IR exporters are established boundaries but
remain active decomposition targets as their supported behavior expands.
CODESYS IR project-integration configuration and naming/default policies are
kept separately from XML serialization in `exporters.codesys_ir_integration`.
Reusable-unit POU interfaces and datatype encoding are isolated in
`exporters.codesys_ir_pou`, with lifecycle and identity behavior supplied
through narrow callbacks.
CODESYS lifecycle eligibility and native method emission are isolated in
`exporters.codesys_ir_lifecycle`; the exporter consumes that single policy
for diagnostics, POU content and project-tree metadata.
CODESYS IR library discovery, native metadata and Library Manager identity
are isolated in `exporters.codesys_ir_libraries`.
`CodesysIRPLCopenExporter` remains the stable façade over these collaborators;
fixed-time regression fixtures protect byte-stable import structure and
deterministic CODESYS object IDs.

The PowerFlex 525 executable core is target-neutral in
`exporters.powerflex525_core`. CODESYS device composition is owned by
`targets.codesys.powerflex525`; compatibility aliases preserve the former
public exporter API while dependency tests protect the neutral boundary.

The CODESYS EtherNet/IP module-service adapter is reusable infrastructure, not
a PowerFlex-only implementation. Its validated boundary normalizes remote
adapter diagnostics, enable state, fault state, diagnostic text, and
capability-gated reconfiguration. Device profiles separately own assembly
instances and sizes, cyclic data layouts, scaling, command/status semantics,
and electronic keying. The PowerFlex 525 profile is the first proven consumer
of that infrastructure. Device-specific parameter access and explicit
messaging remain evidence-gated profile work; they are not yet asserted as a
generic EtherNet/IP messaging implementation.

Generated Python packaging metadata such as `*.egg-info/` is not source and
is intentionally excluded from version control. Package configuration is
owned by `pyproject.toml`.

Architecture tests enforce that neutral model and IR modules do not import
conversion or target layers. Exporter-to-target imports are restricted to
documented compatibility surfaces, and public package exports must be unique
and resolvable.

`targets.openplc` exposes a standards-only PLCopen 2.01 façade and a separate
native project-directory packager, with no direct CODESYS dependency or
emitted CODESYS metadata. The native packager currently accepts only the
evidenced local-BOOL serial and two-path parallel Ladder subset, canonical
Rockwell `TON` and `TOF`/`.DN` pairs, and optional `%MD` `TON` elapsed-time
telemetry. The evidenced adjacent Rockwell `RTO`/`.DN`/`RES` group is lowered
through a generated, target-owned `TF_RTO` compatibility function block. It
rejects other semantics before writing a partial project. Native OpenPLC
editor/runtime compatibility is expanded only after editor, compiler, and
runtime evidence—not by inferring that superficially similar blocks are
interchangeable.

## Invariants

- Unknown source data is preserved.
- Exporters do not parse L5X.
- Source-specific conventions carry explicit provenance.
- Absence of source evidence is not treated as a false fact.
- Model identity and relationships are resolved before export.
- Standard XML validation and semantic reference validation are separate.

## Export architecture

PLCopen XML represents executable IEC 61131-3 project content. AutomationML
represents plant/controller/module/signal context and references PLCopen XML
through the standard `PLCopenXMLInterface`.

```text
AutomationML CAEX hierarchy
├── controller, chassis and modules
├── I/O interfaces and process signals
├── RoleClass / InterfaceClass / AttributeType libraries
├── vendor-neutral and catalog SystemUnitClasses
└── PLCopenXMLInterface → PLCopen XML document
```

## Deferred architecture

- live CIP reconciliation with offline L5X;
- physical Channel and CIP Assembly objects;
- multi-controller communication graphs;
- external protocol maps such as Modbus;
- hardware capability profiles beyond recognized source/catalog evidence.
