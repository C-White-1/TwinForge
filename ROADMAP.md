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
- [x] Deterministic, versioned neutral-model JSON export and validation
- [x] Deterministic neutral-model JSON evidence inventory for people and tools
- [x] Packaged JSON Schema for external neutral-model artifact validation
- [x] Pyright, Ruff, and automated test checks in CI

The current fixture converts all 134 rungs and 474 instruction occurrences.
That is a project-specific result, not universal Logix coverage.

## Next: broaden offline engineering value

### Compatibility corpus

- [ ] Collect legally shareable L5X fixtures from varied Logix systems
- [ ] Add CompactLogix and additional ControlLogix hardware
- [ ] Exercise produced/consumed tags, MSG, AOIs, motion and safety content
- [x] Publish per-fixture rung and instruction coverage
- [x] Add regression fixtures for unknown attributes and elements

### Model and parser depth

- [x] Structured and array initial values
- [ ] UDT and Add-On Instruction semantics
  - [x] Resolve controller-defined UDT references for AOI parameters and local
    tags
  - [x] Promote structured and array defaults for AOI parameters and local tags
  - [x] Bind composite value nodes to controller-defined UDT members
  - [x] Diagnose explicit composite-member and UDT-schema conflicts
  - [x] Resolve UDT bit-overlay targets and diagnose missing target members
  - [x] Link AOI parameter aliases and diagnose missing named targets
  - [x] Resolve AOI aliases through controller-defined UDT member paths
  - [x] Resolve indexed AOI aliases and validate declared array bounds
  - [x] Recognize Logix decorated BIT/BOOL and string-member equivalence
- [ ] Additional task and routine-body forms
  - [x] Promote event-task trigger configuration and validate applicability
  - [x] Promote routine descriptions and validate known body applicability
- [ ] Explicit cross-reference and tag dependency graphs
  - [x] Resolve Ladder and Structured Text call operands with scope, member,
    access-direction, source-location, and unresolved-evidence retention
  - [x] Add direct Structured Text assignment and condition references
  - [x] Add alias-definition dependency edges
  - [ ] Add dependency edges for additional routine-body languages
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

- [x] Evidence-bound channel I/O list with assignments, spare candidates,
  configuration-unavailable channels, ranges, units, and unresolved aliases
- [ ] Alarm and trip list
  - [x] Identify explicitly labelled alarm/trip tag candidates and join their
    reader, writer, alias, scope, and classification evidence
  - [x] Export a candidate list with alarm-philosophy fields kept
    explicitly unknown when absent
  - [x] Apply versioned, attributable, fail-closed engineering review overlays
    without replacing source evidence
  - [x] Validate review-overlay contracts independently of report generation
  - [x] Reconcile standalone review validation against source L5X evidence
  - [x] Emit schema-backed, hash-bound review-validation receipts for automation
  - [x] Return stable validation exit codes and JSON failure diagnostics
  - [x] Persist successful validation receipts with atomic file replacement
  - [ ] Review candidates and validate priorities, setpoints, and actions
    against the applicable alarm philosophy and process design
- [ ] Cause-and-effect matrix
  - [x] Export same-location read/write candidates with resolved and unresolved
    evidence and an explicit unverified-causality state
  - [x] Assign deterministic relationship identities and apply attributable,
    fail-closed engineering dispositions without replacing inferred evidence
  - [x] Report review coverage and remaining field gaps without implying
    engineering approval
  - [x] Emit a deterministic integrity manifest for source evidence, review
    overlays, and generated engineering reports
  - [x] Verify complete report bundles against every manifested source and
    generated file
  - [ ] Validate polarity, voting, delays, operating modes, and shutdown actions
    against process design and the applicable alarm philosophy
- [x] PowerFlex device functional-description draft
- [x] Parameter, setpoint, and engineering-unit reports
- [x] PowerFlex cyclic-I/O, diagnostic, and conversion-readiness reports
- [x] General controller-level functional-description draft aggregating
  identity, execution structure, routine inventory, and engineering evidence
- [x] Module and spare-I/O schedule retaining assigned, spare-candidate,
  configuration-unavailable, and unknown-capability states
- [x] Signal and program dependency reports

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
- [x] Improve repository navigation with architecture diagrams, a
  documentation index, directory responsibilities, and an artifact policy
- [x] Generalize CODESYS bundle packaging and EtherNet/IP manifest data while
  retaining concrete profile-specific native-evidence validation

### User-facing command line

- [x] Add an installed `twinforge` command and module entry point
- [x] Add safe discovery-state initialize, validate, and inspect commands
- [x] Add L5X `inspect` and controller engineering `report` subcommands
- [x] Add target-neutral PLCopen XML 2.01 export with optional XSD validation
- [x] Add the separately adapted CODESYS PLCopen XML export target
- [x] Add native OpenPLC project export for the runtime-evidenced subset
- [x] Add AutomationML export with semantic references and optional CAEX XSD
- [x] Preserve the example scripts as focused demonstrations or thin CLI
  wrappers
- [x] Add versioned OpenPLC target configuration with explicit CLI overrides
- [x] Generalize validated configuration to PLCopen and AutomationML targets
- [x] Add an installed CODESYS deployment command backed by the validated
  PowerFlex manifest and native-template evidence
- [x] Add side-effect-free pre-export readiness through `export --dry-run`
  target output
- [x] Provide stable process exit codes and optional machine-readable
  diagnostics for automation and CI
- [x] Add deterministic CLI integration tests for PLCopen XML, CODESYS,
  native OpenPLC, AutomationML, and reports
- [x] Document installation and offline operation without an AI or network
  service

## Next: communication modelling

Introduce vendor-neutral communication endpoints and mappings rather than
placing protocol registers directly on Rockwell modules or tags.

- [x] Produced/consumed tag relationships
  - [x] Capture specification-defined ProduceInfo and ConsumeInfo fields
  - [x] Preserve unknown produced/consumed attributes as source evidence
  - [x] Resolve only unique controller and remote produced-tag matches
  - [x] Retain unresolved RemoteTag and legacy RemoteFile relationships
- [x] MSG and CIP Generic instruction analysis
  - [x] Resolve Ladder and Structured Text MSG calls to scoped MESSAGE tags
  - [x] Identify CIP Generic only from captured tag configuration evidence
  - [x] Preserve malformed and unresolved MSG calls for engineering review
- [x] External address and controller-reference discovery
  - [x] Inventory module Address and MESSAGE ConnectionPath fields
  - [x] Inventory consumed-tag Producer, RemoteTag, and RemoteFile fields
  - [x] Classify only exact IPv4 literals; retain all other paths symbolically
- [x] Modbus device, area and register-map model
- [x] CSV/manual import for mappings absent from L5X
- [x] Link evidenced communication points to tags and AutomationML interfaces
  - [x] Bind evidenced PLX50 EtherNet/IP assembly points to controller tags
  - [x] Expose neutral communication/tag bindings as AutomationML interfaces
- [x] Multi-controller communication graph
  - [x] Inventory configured MESSAGE evidence without inferred edges
  - [x] Apply explicit versioned controller-workspace bindings
  - [x] Export a deterministic machine-readable graph from the CLI
- [x] Multi-protocol gateway modelling
  - [x] Catalogue PLX51-PBM EDS, GSD, AOI, manuals, and configuration tools
  - [x] Parse EDS identity, assemblies, and Class 1 connection definitions
    - [x] Parse EDS sections losslessly and promote CIP device identity
    - [x] Promote EDS assembly declarations without inferring instances
    - [x] Promote EDS Class 1 connection declarations and raw paths
  - [x] Parse GSD identity, limits, and modular cyclic-data definitions
    - [x] Parse GSD source losslessly and promote identity and station limits
    - [x] Promote selectable modules and standard cyclic-data identifiers
  - [x] Model gateway protocol endpoints without conflating their mappings
    - [x] Correlate paired EDS/GSD descriptions into unmapped endpoints
  - [x] Ingest PLX50 configuration exports or generated mapping reports
    - [x] Add neutral CSV/manual mapping-report ingestion
    - [x] Decode native PSJ containers and preserve project XML
    - [x] Apply native operating mode and primary endpoint configuration
    - [x] Apply native Modbus address, unit, port, and base convention
    - [x] Lower evidenced built-in Modbus register-region bases
    - [x] Parse configured PROFIBUS devices, slots, and data points
  - [x] Correlate configured PROFIBUS points, CIP offsets, Modbus registers,
    and controller tags
    - [x] Correlate configured PROFIBUS data points with Modbus registers
    - [x] Preserve bidirectional PROFIBUS/Modbus mapping flow
    - [x] Parse generated Logix mapping context and retain its source rungs
    - [x] Correlate generated UDT members with CPS assembly transfers
    - [x] Render deterministic PLX50 Logix mapping review reports
    - [x] Publish a versioned machine-readable PLX50 mapping contract

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
- [x] Bounded `pycomm3` CIP Identity adapter
- [x] Bounded CIP chassis/slot discovery with typed slot outcomes
- [x] Controller metadata and structural program, routine, task, and tag
  discovery
  - [ ] Verify experimental Logix Symbol pagination on an authorized controller
- [x] Assembly and connection-manager discovery
  - [x] Add explicit specification-attributed, request-budgeted read plans
  - [x] Add raw evidence capture behind a preflighted execution permit
  - [x] Decode only profile-defined assembly and connection-manager fields
  - [x] Add a read-only routed `pycomm3` transport for exact planned requests
  - [x] Derive exact Assembly read candidates from EDS logical path evidence
  - [ ] Validate the transport against authorized physical devices

- [x] EtherNet/IP topology and bridge-evidence correlation
- [x] Compare discovered CIP identity with explicitly bound offline L5X modules
- [x] Detect hardware, firmware, configuration, and network drift

### Offline PROFINET packet evidence

- [ ] Admit lawful PCAP and PCAPNG sources through versioned provenance,
  checksum, sanitization, and resource-limit manifests
- [ ] Qualify discovery, configuration, and sustained cyclic PROFINET traffic
  without treating capture loss as a telegram gap
- [ ] Add evidence-preserving per-stream timing analysis only after capture
  quality is established
- [ ] Correlate qualified traffic with GSDML and neutral communication
  endpoints

The phased evidence and safety boundary is documented in the
[PROFINET PCAP analysis roadmap](docs/roadmaps/profinet-pcap-roadmap.md).

The conservative planning and evidence boundary is documented in
[CIP Infrastructure Discovery](docs/architecture/cip-infrastructure-discovery.md).

The phased safety, evidence, adapter, laboratory, and reconciliation plan is in
[Authorized Online Discovery Roadmap](docs/roadmaps/online-discovery-roadmap.md).

## Additional inputs and outputs

- [x] Lossless EDS parser with identity, assembly, connection, and CIP-path
  evidence promotion
- [x] Lossless GSD parser with identity, station-limit, module, and cyclic-data
  evidence promotion
- [ ] Broaden EDS and GSD device-profile coverage with additional lawful
  fixtures
- [x] Deterministic, cycle-safe JSON export of converted model and retained
  source evidence
- [ ] Asset Administration Shell
- [ ] Graphviz and graph-database exports
- [ ] OPC UA information model
- [ ] IEC 62424 and IEC 81346 mappings
- [ ] HMI tag correlation and cable schedules

## Someday goals

These are strategic possibilities rather than near-term commitments. They
must build on stable application services and must not weaken TwinForge's
evidence, authorization, or vendor-neutral boundaries.

- [ ] Investigate mappings from the TwinForge model to Asset Administration
  Shell and CESMII i3X Smart Manufacturing Profiles.
  - Preserve provenance, confidence, engineering units, ranges, hierarchy and
    unknown source evidence.
  - Treat AAS and i3X as semantic output profiles rather than replacements for
    the vendor-neutral core.
  - Evaluate alignment with AutomationML, PLCopen XML, ISA-95 and Unified
    Namespace conventions before selecting mappings.
- [ ] Evaluate a governed, read-only Model Context Protocol adapter.
  - Place MCP outside the core as an adapter over stable application services.
  - Keep the CLI, Python API and non-agent workflows fully usable without MCP.
  - [x] Establish versioned model JSON, schema, validation, inventory, and
    read-only JSON Pointer query services beneath any future adapter.
  - [x] Add deterministic typed-record discovery returning queryable pointers.
  - [x] Add deterministic structural comparison of validated model artifacts.
  - Expose bounded controller, program, routine, tag-reference, AOI,
    diagnostic, communication, comparison, and report queries.
  - Add deterministic code-review findings with stable source pointers,
    confidence classes, and explicit separation from AI recommendations.
  - Evaluate an explainable brownfield-change assessment whose rubric,
    weights, unavailable evidence, and uncertainty are visible.
  - Keep drawings, manuals, and other retrieved engineering artifacts under
    separate provenance, licensing, revision, and confidence records.
  - Support customer-controlled and offline deployment with explicit model,
    prompt, retention, and telemetry policies.
  - Expose narrowly scoped inspection, conversion, reporting, planning and
    authorized capture operations instead of arbitrary protocol primitives.
  - Require nonhuman identity, least privilege, explicit permits, request
    budgets, audit evidence and human acceptance for consequential actions.
  - Do not assume MCP transport provides industrial safety, authorization or
    semantic interoperability by itself.
  - Defer live-value polling, history, continuous troubleshooting, and safety
    interpretation to separately authorized and laboratory-validated phases.
  - Do not claim portable ACD conversion until its Rockwell dependencies,
    licence, platform requirements, and loss behavior are evidenced.
  - See the
    [Plantwide Integration L5X and MCP analysis](docs/references/plantwide-l5x-mcp-analysis.md).
- [ ] Evaluate IEC 61499 generation and Eclipse 4diac FORTE deployment.
  - Establish native localhost evidence before generating project files.
  - Treat Allen-Bradley controllers as external devices, not FORTE targets.
  - Define event scheduling explicitly before translating Logix behavior.
  - See the
    [IEC 61499 and Eclipse 4diac roadmap](docs/roadmaps/iec61499-4diac-roadmap.md).

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
