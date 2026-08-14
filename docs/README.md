# TwinForge Documentation

This page is the landing point for TwinForge user, contributor, architecture,
target, experiment, and reference documentation. The root
[README](../README.md) provides the concise project introduction and command
examples; this index routes to the detailed material.

## Getting started

- [Installation, CLI usage, and offline operation](offline-usage.md)
- [Supported standalone L5X document types](l5x-documents.md)
- [Example catalogue](examples.md)
- [Main capability roadmap](../ROADMAP.md)

The installed `twinforge` command is the supported user interface. Example
scripts are compatibility wrappers or focused Python API demonstrations, not a
second command-line product.

## Architecture and model

- [Architecture overview and rendered diagrams](../ARCHITECTURE.md)
- [Vendor-neutral domain model](../MODEL.md)
- [Architecture decisions](../DECISIONS.md)
- [Architecture and refactoring roadmap](roadmaps/architecture-refactoring-roadmap.md)
- [Executable intermediate representation](executable-ir.md)
- [Structured Text front end](structured-text.md)
- [Tag dependency graph](architecture/tag-dependency-graph.md)
- [Controller functional-description aggregation](architecture/controller-functional-description.md)

The authoritative PlantUML sources and GitHub-renderable SVGs are under
[`architecture/diagrams/`](architecture/diagrams/). The sources define the
maintained relationships; the SVG files are derived viewing artifacts.

## Conversion targets

- [Cross-target capability matrix](capability-matrix.md)

### PLCopen XML and CODESYS

- [PLCopen capability matrix](plcopen-capabilities.md)
- [PLCopen standards and local schema handling](standards/plcopen.md)
- [AOI portability and runtime contracts](aoi-portability.md)
- [CODESYS EtherNet/IP module adapter](architecture/codesys-ethernetip-module-adapter.md)
- [Neutral model JSON contract](architecture/model-json-contract.md)

### Native OpenPLC

- [Native OpenPLC compatibility and validation](experiments/OpenPLC-native-project-compatibility.md)
- [Counter execution semantics](architecture/counter-execution.md)

Native OpenPLC generation is a separate target path because the observed
OpenPLC editor stores working projects in its own directory and `.ld` JSON
representation rather than importing the tested PLCopen XML exchange output.

### IEC 61499 and Eclipse 4diac

- [IEC 61499 and Eclipse 4diac target roadmap](roadmaps/iec61499-4diac-roadmap.md)

IEC 61499 is a prospective, distinct distributed-automation target. The first
gate is a native 4diac project deployed to a localhost FORTE runtime; TwinForge
does not currently generate IEC 61499 artifacts.

### AutomationML

- [AutomationML capability and proof of concept](automationml-proof-of-concept.md)
- [AutomationML standards and local reference handling](standards/automationml.md)
- [I/O list evidence](architecture/io-list.md)
- [Module and spare-I/O schedule](architecture/module-schedule.md)

## Engineering reports

- [Parameter, setpoint, range, and unit reports](parameter-reports.md)
- [Alarm and trip candidates](architecture/alarm-trip-candidates.md)
- [Cause-and-effect candidates](architecture/cause-effect-candidates.md)
- [I/O list](architecture/io-list.md)
- [Module and spare-I/O schedule](architecture/module-schedule.md)
- [Controller functional-description draft](architecture/controller-functional-description.md)

Candidate reports retain uncertainty. They do not replace alarm-philosophy,
process-design, wiring, safety, or commissioning review.

## Discovery and communication modelling

- [Authorized online discovery roadmap](roadmaps/online-discovery-roadmap.md)
- [Discovery drift and acceptance](architecture/discovery-drift.md)
- [Controller communication graph](architecture/controller-communication-graph.md)
- [CIP identity adapter](architecture/pycomm3-identity-adapter.md)
- [CIP routed capture](architecture/cip-routed-capture.md)
- [SNMP request safety](architecture/snmp-request-safety-policy.md)
- [SNMPv3 read-only security](architecture/snmpv3-read-only-security.md)
- [Accepted network graph](architecture/accepted-network-graph.md)

Live acquisition is evidence-gated and authorization-bound. Offline files,
simulators, and explicitly authorized laboratory targets are the normal test
sources; public-address probing is outside the supported workflow.

## Experiments and target evidence

- [CODESYS Sys_Module and PowerFlex 525 experiment](experiments/Sys_Module-PowerFlex525-CODESYS.md)
- [CODESYS visualization differential testing](references/CODESYS-visualization-differential-testing.md)
- [OpenPLC native-project compatibility](experiments/OpenPLC-native-project-compatibility.md)
- [pycomm3 software-inventory laboratory validation](experiments/pycomm3-software-inventory-lab-validation.md)
- [SNMPSim data compatibility](experiments/snmpsim-data-compatibility.md)

Experiment documents record observed tool or runtime behavior. They are not
automatically general product guarantees.

## Device and feature roadmaps

- [RTC_PulseGen AOI](roadmaps/RTC_PulseGen-AOI-roadmap.md)
- [Sys_Module AOI](roadmaps/Sys_Module-AOI-roadmap.md)
- [Online discovery](roadmaps/online-discovery-roadmap.md)
- [Architecture and refactoring](roadmaps/architecture-refactoring-roadmap.md)
- [IEC 61499 and Eclipse 4diac](roadmaps/iec61499-4diac-roadmap.md)
- [PROFINET PCAP analysis](roadmaps/profinet-pcap-roadmap.md)

## Reference provenance

- [Artifact and tracking policy](artifact-policy.md)
- [August 2026 tracked-artifact audit](artifact-audit-2026-08.md)
- [PowerFlex 525 reference notes](references/PowerFlex525.md)
- [PLCopen source and schema handling](standards/plcopen.md)
- [AutomationML source and schema handling](standards/automationml.md)
- [PROFINET PCAP source catalogue](references/profinet-pcap-sources.md)

The repository's `reference/` directory is intentionally ignored. Standards,
schemas, manuals, native editor exports, packet captures, and other externally
obtained evidence must be acquired lawfully, retained with provenance, and
kept out of Git unless redistribution rights and the artifact policy explicitly
permit tracking them.

## Historical and specialist notes

The `docs/` root also contains early research notes and specialist cheat sheets.
They remain available as evidence but are not authoritative architecture or
capability declarations unless linked from the sections above. When documents
conflict, prefer the current root README, architecture overview, capability
roadmap, target capability documents, and tested behavior.
