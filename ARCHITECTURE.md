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
| `exporters` | PLCopen XML and AutomationML generation and validation |
| `cip`, `discovery` | Future/live controller and network acquisition |

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
