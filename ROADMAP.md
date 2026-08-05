# TwinForge roadmap

TwinForge is evolving from an L5X parser into a vendor-neutral industrial
automation engineering toolkit. The roadmap distinguishes verified capability
from intended work.

Architecture and technical-debt work is tracked separately in the
[architecture and refactoring roadmap](docs/roadmaps/architecture-refactoring-roadmap.md).
Capability changes and structural changes must update the relevant roadmap in
the same commit.

## Current foundation

- [x] Specification-driven, lossless L5X capture
- [x] Vendor-neutral controller, chassis, module and identity model
- [x] Electronic-key, connection and module-parent conversion
- [x] Datatypes, controller tags, program tags and scalar exported values
- [x] Programs, routines, RLL rungs, tasks and scheduled-program references
- [x] Add-On Instruction parameters, local tags, dependencies and Structured
  Text source capture
- [x] AOI portability, runtime-capability and PLCopen Common Behaviour analysis
- [x] Engineering-unit and analogue-range evidence with provenance
- [x] Project-specific RLL conversion coverage reports
- [x] PLCopen XML 2.01 and CODESYS-targeted export
- [x] CODESYS import and precompile validation for the Booster Compressor
- [x] AutomationML 2.1 / CAEX 3.0 export and validation
- [x] AutomationML semantic libraries, typed instances and PLCopen references
- [x] Nominal, configured, unavailable, assigned and spare I/O reporting
- [x] Manual-backed semantics for all 163 PowerFlex 525 parameters observed by
  the reference AOI bulk-read implementation
- [x] Typed executable IR and tested Structured Text AOI conversion for
  `Str_Capacity` and `RTC_PulseGen`
- [x] CODESYS lifecycle, wall-clock, EtherNet/IP diagnostic, and
  reconfiguration target adapters
- [x] Native OpenPLC project generation with runtime-validated Boolean,
  branch, seal-in, timer, retained-timer, and shared-counter semantics
- [x] Single-drive and multi-drive PowerFlex 525 CODESYS applications
- [x] Pydantic-validated CODESYS deployment manifests and reproducible
  native-device/PLCopen bundles
- [x] Responsibility-focused L5X module and AutomationML components
- [x] Pyright, Ruff, and automated test checks in CI

The current fixture converts all 134 rungs and 474 instruction occurrences.
That is a project-specific result, not universal Logix coverage.

## Next: broaden offline engineering value

### Compatibility corpus

- [ ] Collect legally shareable L5X fixtures from varied Logix systems
- [ ] Add CompactLogix and additional ControlLogix hardware
- [ ] Exercise produced/consumed tags, MSG, AOIs, motion and safety content
- [ ] Publish per-fixture rung and instruction coverage
- [ ] Add regression fixtures for unknown attributes and elements

### Model and parser depth

- [ ] Structured and array initial values
- [ ] UDT and Add-On Instruction semantics
- [ ] Additional task and routine-body forms
- [ ] Explicit cross-reference and tag dependency graphs
- [ ] Physical channel and CIP assembly entities when supported by evidence

### PLCopen conversion

- [ ] Complex and nested branches
- [ ] Generic PLCopen lowering for TOF, RTO, counters and sequencers
- [ ] Additional comparison, bit, file and data-handling instructions
- [x] Executable Structured Text subset through typed, vendor-neutral IR
- [ ] Broaden Structured Text beyond the tested AOI subset
- [ ] Function Block Diagram and SFC bodies
- [ ] UDT, array and AOI representation
- [x] General AOI-to-IEC Structured Text pipeline and target-runtime adapter
  boundary established with two successful AOIs
- [x] Convert `RTC_PulseGen` using the general AOI pipeline and the CODESYS
  high-resolution wall-clock adapter; see the
  [RTC_PulseGen AOI roadmap](docs/roadmaps/RTC_PulseGen-AOI-roadmap.md)
- [ ] Broaden AOI conversion to additional instructions, datatypes, nested
  calls, and lifecycle combinations
- [ ] Add optional PLCopen Common Behaviour wrappers after underlying AOI
  translation is semantically validated
- [ ] Produced/consumed and physical I/O binding strategies

This section describes the portable PLCopen XML exporter. Native OpenPLC
project generation is a separate target path because the observed OpenPLC
editor does not import PLCopen XML and instead stores ladder programs in its
own project-directory and `.ld` JSON representation.

### Native OpenPLC conversion

- [x] Generate deterministic OpenPLC project directories and ladder POUs
- [x] Validate serial contacts, parallel paths, coils and seal-in circuits
- [x] Lower and runtime-test Rockwell `TON`, `TOF`, `RTO`, and adjacent `RES`
- [x] Expose runtime-tested `TON.ET` telemetry through an optional `%MD`
  location
- [x] Lower standalone and paired Rockwell `CTU`/`CTD` instructions through
  one shared `TF_COUNTER` state owner
- [x] Preserve counter preset, accumulator, done, overflow, underflow, reset,
  source order, and signed-DINT rollover semantics for the supported shapes
- [x] Compile and runtime-test CTU-only, paired, simultaneous-edge, overflow,
  and underflow fixtures
- [ ] Acquire legally shareable, authentic Logix counter fixtures for
  independent source-shape validation
- [ ] Support additional timer and counter arrangements only when source
  evidence defines their execution and reset boundaries
- [ ] Add comparison, arithmetic, move, one-shot, and further data-handling
  instructions
- [ ] Broaden nested and multi-leg branch lowering
- [ ] Establish an OpenPLC wall-clock adapter for `RTC_PulseGen`
- [ ] Publish per-fixture native OpenPLC conversion coverage

### Automatic engineering documents

- [ ] I/O list
- [ ] Alarm and trip list
- [ ] Cause-and-effect matrix
- [x] PowerFlex device functional-description draft
- [x] Parameter, setpoint, and engineering-unit reports
- [x] PowerFlex cyclic-I/O, diagnostic, and conversion-readiness reports
- [ ] General controller-level functional-description generation
- [ ] Module and spare-I/O schedule
- [ ] Signal and program dependency reports

### Architecture maintenance

The immediate structural priorities are maintained in the
[architecture and refactoring roadmap](docs/roadmaps/architecture-refactoring-roadmap.md):

- [x] Split instruction, operand, variable, and project responsibilities out
  of the general PLCopen exporter
- [x] Divide CODESYS IR POU serialization from task, project, lifecycle, and
  library metadata
- [x] Move PowerFlex-specific CODESYS composition beneath `targets.codesys`
- [x] Split native OpenPLC validation, declaration, instruction lowering,
  graph serialization, and project-file packaging behind its stable exporter
  façade
- [ ] Improve repository navigation with architecture diagrams, a
  documentation index, directory responsibilities, and an artifact policy
- [ ] Generalize deployment packaging only after a second real device profile
  establishes the reusable boundary

### User-facing command line

- [x] Add an installed `twinforge` command and module entry point
- [x] Add safe discovery-state initialize, validate, and inspect commands
- [x] Add L5X `inspect` and controller engineering `report` subcommands
- [ ] Add L5X target `export` subcommands
- [ ] Preserve the example scripts as focused demonstrations or thin CLI
  wrappers
- [ ] Add Pydantic-validated target configuration files and explicit command
  overrides
- [ ] Report conversion readiness and unsupported semantics before writing
  target output
- [ ] Provide stable process exit codes and optional machine-readable
  diagnostics for automation and CI
- [ ] Add deterministic CLI integration tests for PLCopen XML, CODESYS,
  native OpenPLC, AutomationML, and reports
- [ ] Document installation and offline operation without an AI or network
  service

## Next: communication modelling

Introduce vendor-neutral communication endpoints and mappings rather than
placing protocol registers directly on Rockwell modules or tags.

- [ ] Produced/consumed tag relationships
- [ ] MSG and CIP Generic instruction analysis
- [ ] External address and controller-reference discovery
- [ ] Modbus device, area and register-map model
- [ ] CSV/manual import for mappings absent from L5X
- [ ] Link communication points to tags, signals and AutomationML interfaces
- [ ] Multi-controller communication graph

The Booster Compressor fixture contains no confirmed Modbus register map.
Protocol mappings must therefore remain external evidence unless another
source explicitly supplies them.

## Online discovery and reconciliation

- [x] Offline Discovery Snapshot v1 contracts, fake provider and stable JSON
- [x] Offline SNMP node, interface, LLDP and forwarding evidence contracts
- [x] Local SNMPSim fixture and bounded read-only SNMP adapter
- [x] SNMPREC and Net-SNMP walk ingestion with retained unknown evidence
- [x] RFC 6933 physical inventory, containment validation, and candidates
- [x] CIP, physical-entity, and explicitly bound L5X module reconciliation
- [x] Auditable acceptance staging without direct core-model mutation
- [x] Cross-capture generations and explicit supersede, merge, and split events
- [x] Explicit reversible promotion into vendor-neutral assets and devices
- [x] Atomic Plant promotion repository boundary with idempotent replay
- [x] Versioned atomic JSON persistence for lifecycle and promotion state
- [ ] Bounded `pycomm3` CIP Identity adapter
- [ ] CIP chassis/slot discovery
- [ ] Controller, program, routine and tag discovery
- [ ] Assembly and connection-manager discovery
- [ ] EtherNet/IP topology and bridge discovery
- [x] Compare discovered CIP identity with explicitly bound offline L5X modules
- [ ] Detect hardware, firmware and network drift

The phased safety, evidence, adapter, laboratory, and reconciliation plan is in
[Authorized Online Discovery Roadmap](docs/roadmaps/online-discovery-roadmap.md).

## Additional inputs and outputs

- [ ] EDS parser and module capability profiles
- [ ] JSON model export
- [ ] Asset Administration Shell
- [ ] Graphviz and graph-database exports
- [ ] OPC UA information model
- [ ] IEC 62424 and IEC 81346 mappings
- [ ] HMI tag correlation and cable schedules

## Deferred model entities

`Channel` and CIP `Assembly` remain deferred until module profiles or live
discovery provide enough evidence. AutomationML interfaces currently describe
known or capacity-derived points without claiming that full physical channel
objects have been discovered.

## Guiding principles

1. Never discard source data.
2. Prefer specification or protocol evidence over heuristics.
3. Record provenance and confidence when inference is necessary.
4. Keep the core model vendor-neutral.
5. Keep capture, conversion, analysis and export independently testable.
6. Do not confuse successful import with runtime semantic equivalence.
