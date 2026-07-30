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
- [ ] TOF, RTO, counters and sequencers
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

- split instruction, operand, variable, and project responsibilities out of
  the general PLCopen exporter;
- divide CODESYS IR POU serialization from task, project, lifecycle, and
  library metadata;
- move PowerFlex-specific CODESYS composition beneath `targets.codesys`; and
- generalize deployment packaging only after a second real device profile
  establishes the reusable boundary.

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

- [ ] CIP Identity and chassis/slot discovery
- [ ] Controller, program, routine and tag discovery
- [ ] Assembly and connection-manager discovery
- [ ] EtherNet/IP topology and bridge discovery
- [ ] Compare online state with offline L5X
- [ ] Detect hardware, firmware and network drift

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
