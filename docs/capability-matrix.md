# Cross-Target Capability Matrix

This matrix summarizes TwinForge's tested boundaries across source capture,
the vendor-neutral model, and its principal output targets. It is a navigation
aid, not a substitute for the detailed target documents or conversion
diagnostics.

## Status legend

- **I — Implemented:** covered by maintained automated tests for the stated
  scope.
- **P — Partial:** useful behavior exists, but relevant source shapes or
  semantics remain unsupported.
- **E — Evidence-gated:** implemented for named fixtures or observed native
  behavior; do not generalize without further evidence.
- **U — Unsupported:** recognized as outside the current target boundary.
- **N — Not applicable:** the layer or target does not own this concern.

Successful parsing, schema validation, editor import, compilation, and runtime
equivalence are distinct claims. An `I` in one column does not imply an `I` in
the columns to its right.

## Core structure and data

| Capability | Capture | Model | PLCopen | CODESYS | OpenPLC | AML |
| --- | --- | --- | --- | --- | --- | --- |
| Controller identity | I | I | P | P | N | I |
| Chassis and modules | I | I | N | N | N | I |
| Electronic keying | I | I | N | N | N | P |
| Connections | I | I | N | N | N | P |
| Tasks and programs | I | I | I | I | P | P |
| Routines and actions | I | I | P | I | P | N |
| Scalar tags and values | I | I | I | I | P | P |
| Program-scoped tags | I | I | I | I | P | N |
| Arrays and structures | P | P | U | U | U | N |
| UDT definitions | I | I | U | U | U | N |
| Produced/consumed tags | P | P | U | U | U | N |
| Unknown L5X content | I | I | P | P | U | P |

`Capture` means lossless, specification-driven L5X capture. `Model` means a
typed vendor-neutral representation or retained source extension. Partial
preservation in an output may use extension metadata and does not make the
content executable there.

## Logic conversion

| Capability | Capture | Model | PLCopen | CODESYS | OpenPLC | AML |
| --- | --- | --- | --- | --- | --- | --- |
| RLL source and comments | I | I | I | I | P | N |
| Contacts and coils | I | I | P | I | E | N |
| Top-level branches | I | I | P | I | E | N |
| Nested branches | I | I | U | U | U | N |
| Comparisons | I | I | P | I | U | N |
| Move and arithmetic | I | I | P | I | U | N |
| TON | I | I | P | I | E | N |
| TOF and RTO | I | I | U | U | E | N |
| CTU and CTD | I | I | U | U | E | N |
| ONS | I | I | P | I | U | N |
| JSR action calls | I | I | P | I | U | N |
| Arbitrary RLL | I | I | U | U | U | N |
| Structured Text source | I | I | P | P | U | N |
| Tested ST AOIs | I | I | P | E | U | N |
| FBD and SFC bodies | P | P | U | U | U | N |

The CODESYS Booster Compressor fixture imports and precompiles with all 134
rungs and 474 instruction occurrences executable for that project. This is not
a percentage of the Logix instruction catalogue.

Native OpenPLC status is evidence-gated because its packager accepts only
runtime-tested source shapes. Current evidence covers local Boolean serial and
parallel logic, seal-in circuits, TON, TOF, RTO/RES, and shared CTU/CTD counter
semantics. Unsupported semantics fail before a partial project is written.

The tested Structured Text AOI conversions are `Str_Capacity` and
`RTC_PulseGen` through executable IR and CODESYS adapters. They do not establish
arbitrary AOI or Structured Text portability.

## Engineering context and output

| Capability | Capture | Model | PLCopen | CODESYS | OpenPLC | AML |
| --- | --- | --- | --- | --- | --- | --- |
| Units and ranges | I | I | P | P | N | I |
| I/O capacity | P | P | N | N | N | P |
| I/O assignments | P | P | U | U | P | P |
| Physical channels | N | U | N | N | P | P |
| CIP assemblies | P | U | N | N | P | P |
| Device parameters | P | I | N | P | N | P |
| PLCopen document link | N | I | N | N | N | I |
| Semantic class libraries | N | I | N | N | N | I |
| Engineering reports | N | I | N | N | N | N |

The neutral model currently retains channel evidence without claiming that
independently discovered physical `Channel` or CIP `Assembly` entities exist.
AutomationML interfaces describe supported evidence; native OpenPLC pin
mappings are target configuration rather than reconstructed Logix wiring.

The engineering report bundle is a separate output family over the neutral
model and analyses. It currently produces controller, program, module, tag,
dependency, I/O, alarm/trip candidate, cause/effect candidate, functional
description, and spare-I/O evidence. Reports do not certify plant intent.

## Validation evidence

| Validation | PLCopen | CODESYS | OpenPLC | AML |
| --- | --- | --- | --- | --- |
| Deterministic automated tests | I | I | I | I |
| Official XSD validation | I | N | P | I |
| Native editor load or import | N | E | E | E |
| Native compile or precompile | N | E | E | N |
| Runtime behavior tests | N | E | E | N |

The standard PLCopen XML 2.01 profile supports optional official XSD
validation. The CODESYS dialect contains native extensions and does not claim
conformance to that standard schema. AutomationML supports CAEX 3.0 XSD plus
separate semantic-reference validation.

The OpenPLC editor exposes PLCopen XML export but no observed corresponding
import. TwinForge therefore provides standards XML for exchange and comparison,
while actual OpenPLC loading uses the separately tested native project format.

## Communication and discovery boundary

Offline SNMP ingestion, bounded read-only SNMP capture, accepted network graphs,
CIP identity, routed chassis evidence, reconciliation, and discovery-state
persistence are implemented outside these conversion columns. Live controller
software inventory, assembly discovery, EtherNet/IP topology, and drift
detection remain evidence- and authorization-gated roadmap work.

## Detailed sources

- [PLCopen and CODESYS capabilities](plcopen-capabilities.md)
- [Native OpenPLC compatibility](experiments/OpenPLC-native-project-compatibility.md)
- [AutomationML capability and validation](automationml-proof-of-concept.md)
- [Main capability roadmap](../ROADMAP.md)
- [Artifact policy](artifact-policy.md)

When this matrix and a target-specific document appear inconsistent, use the
more specific document and current automated behavior, then update the matrix
in the same change.
