# Architecture

TwinForge separates source-specific capture from its vendor-neutral model and
output formats.

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

## Package responsibilities

| Package | Responsibility |
| --- | --- |
| `schema.l5x` | Declarative L5X element and attribute specifications |
| `parsers.l5x` | Generic, lossless XML capture |
| `converters.l5x` | Source-specific conversion and reference resolution |
| `model` | Vendor-neutral domain objects and source provenance |
| `analysis` | Coverage and relationship analysis |
| `structured_text` | Lossless ST syntax and semantic analysis |
| `ir` | Typed, vendor-neutral executable representation and normalization |
| `runtime` | Vendor-neutral runtime contracts and executable reference behavior |
| `exporters` | Generic IEC, PLCopen XML, AutomationML and report generation |
| `targets` | Runtime-specific adapters and deployment packaging |
| `assembly` | Multi-document/controller assembly and software-device resolution |
| `transport`, `discovery` | CIP communication and live acquisition |

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
