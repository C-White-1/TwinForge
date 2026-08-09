# Authorized Online Discovery Roadmap

## Objective

Add read-only industrial asset discovery to TwinForge without coupling the
vendor-neutral model to `pycomm3`, a particular controller family, or a live
network. Discovery must produce evidence that can be retained, reviewed, and
reconciled with offline L5X content.

This roadmap does not authorize scanning. Every live capture must operate
inside an explicit scope supplied by the system owner or laboratory operator.

## Safety and evidence boundary

- Require an engagement name, authorization reference, and explicit targets.
- Default to read-only protocol operations.
- Do not derive targets from public search engines or probe public addresses.
- Apply bounded timeouts, rate limits, route limits, and request budgets in the
  future live adapter.
- Record observations separately from interpretations and inferred topology.
- Preserve raw response evidence and unknown attributes where practical.
- Record timeouts and unsupported services as diagnostics, not missing assets.
- Keep credentials, serial numbers, addresses, and exported evidence out of
  public fixtures unless deliberately sanitized.

## Phase 1: offline Discovery Snapshot v1

- [x] Define explicit discovery scope and target contracts
- [x] Define vendor-neutral CIP Identity observations
- [x] Define a provider protocol independent of `pycomm3`
- [x] Capture deterministic, timezone-aware snapshots
- [x] Preserve raw payload and attribute evidence
- [x] Record target-level provider failures as diagnostics
- [x] Provide deterministic JSON serialization
- [x] Provide a fake provider for tests and demonstrations
- [ ] Add a command-line entry point for fake snapshot generation
- [ ] Add a checked-in sanitized snapshot fixture

No code in this phase opens a socket or communicates with a controller.

## Phase 2: bounded `pycomm3` identity adapter

- [x] Validate targets against authorization and address policy
- [x] Permit only explicit, configured targets
- [x] Implement CIP List Identity or Identity Object reads
- [x] Set conservative timeout and request-rate defaults
- [x] Enforce per-target and per-capture request budgets
- [x] Capture adapter/library version and protocol-operation provenance
- [x] Preserve raw replies when the library exposes them
- [x] Add an operator confirmation or dry-run display before live capture
- [ ] Verify against a local simulator or authorized laboratory only

The implemented boundary and deliberately excluded operations are documented
in the [bounded pycomm3 Identity adapter](../architecture/pycomm3-identity-adapter.md).

## Parallel track: SNMP network evidence

- [x] Define observed SNMP nodes without inferring topology
- [x] Capture system, interface, address, LLDP and forwarding-table evidence
- [x] Preserve numeric SNMP states and raw OID values
- [x] Keep SNMP behind its own provider protocol
- [x] Extend deterministic Discovery Snapshot JSON with SNMP evidence
- [x] Add an offline fake managed-switch fixture
- [x] Add a sanitized SNMPSim managed-switch recording
- [x] Document a loopback-only SNMPSim launch configuration
- [x] Add an offline SNMPSim recording provider and evidence lowerer
- [x] Select maintained PySNMP 7.1 for the optional live client adapter
- [x] Implement a bounded, loopback-only PySNMP v2c laboratory adapter
- [x] Verify live capture against the local sanitized SNMPSim fixture
- [x] Add SHA-256 authenticated, AES-128 private SNMPv3 loopback capture
- [x] Keep SNMPv3 credentials outside snapshots and object representations
- [x] Add a licence-aware, offline SNMP recording corpus manifest
- [x] Report per-recording SNMP evidence coverage and unsupported formats
- [x] Add common Net-SNMP `.snmpwalk` ingestion with unknown-line retention
- [x] Evaluate the BSD-licensed `snmpsim-data` corpus without vendoring it
- [ ] Add a controlled conversion workflow for unusual walk representations
- [x] Classify standard and enterprise OID-family coverage
- [x] Lower RFC 6933 ENTITY-MIB v4 physical inventory and containment evidence
- [x] Validate ENTITY-MIB parent references and containment cycles
- [x] Add ENTITY-MIB to the bounded live-adapter OID allowlist
- [x] Lower ENTITY-MIB rows into evidence-backed physical asset candidates
- [x] Withhold invalid containment edges while retaining validation findings
- [x] Compare physical candidates with exact same-target CIP identity evidence
- [x] Compare explicitly bound L5X modules with discovered CIP identities
- [x] Link corroborated physical candidates without merging model objects
- [ ] Implement specification-backed electronic-key compatibility evaluation
- [x] Add attributable accept, reject, and defer review records
- [x] Require explicit overrides for conflicting or insufficient comparisons
- [x] Build durable staging identities without mutating the core model
- [x] Append immutable identity generations across accepted captures
- [x] Require explicit directives for supersede, merge, and split transitions
- [x] Keep capture absence distinct from asset retirement
- [x] Promote active identities into explicit generic assets or devices
- [x] Retain reversible lifecycle and evidence links on promotion records
- [x] Require renewed acknowledgement of accepted conflict overrides
- [x] Define atomic promotion-repository and Plant integration boundaries
- [x] Add idempotent replay and forward-only generation update rules
- [x] Add schema-versioned atomic JSON lifecycle and promotion persistence
- [x] Reject stale revisions, history loss, and malformed persisted state
- [x] Add installed CLI commands to initialize, validate, and inspect state
- [ ] Implement a transactional multi-writer promotion-repository adapter
- [ ] Add approved chassis and module topology-promotion mappings
- [ ] Evaluate RMON statistics as a separate observation profile
- [ ] Evaluate OSPF evidence only in the routed-topology phase
- [ ] Implement read-only SNMPv3 credentials and security-level configuration
- [ ] Enforce OID allowlists, timeouts, request budgets, and rate limits
- [ ] Lower observed interfaces and neighbours into the network graph
- [ ] Correlate SNMP neighbours and forwarding entries with CIP identities

## Phase 3: routed controller and chassis evidence

- [ ] Add bounded, explicit CIP route declarations
- [ ] Read controller identity and controller metadata
- [ ] Enumerate configured chassis slots within an explicit route limit
- [ ] Distinguish no response, empty slot, unsupported route, and device fault
- [ ] Preserve vendor-specific evidence without placing it in the core model
- [ ] Compare discovered modules with L5X module and electronic-key evidence

## Phase 4: software and tag inventory

- [ ] Discover programs, routines, tasks, and tags only when supported
- [ ] Separate metadata reads from runtime value reads
- [ ] Require a separate policy decision before reading runtime values
- [ ] Avoid exposing tag values in default reports
- [ ] Reconcile discovered software identity with offline L5X sources

## Phase 5: topology and drift

- [x] Correlate LLDP and bridge evidence into topology candidates
- [x] Preserve indirect reachability separately from reported neighbours
- [x] Add qualitative confidence and raw evidence references
- [x] Serialize topology candidates deterministically
- [ ] Define an acceptance policy for lowering candidates into the core model
- [ ] Build an evidence-backed multi-controller communication graph
- [ ] Correlate configured modules, routed observations, and software devices
- [ ] Detect hardware, firmware, configuration, and network drift
- [ ] Export sanitized change reports with confidence and provenance
- [ ] Keep inferred relationships visibly distinct from observed relationships

Correlation semantics and the future lowering boundary are documented in
[Discovery Topology Correlation](../architecture/discovery-topology-correlation.md).
The separate physical-inventory boundary is documented in
[SNMP Physical Asset Candidates](../architecture/snmp-physical-asset-candidates.md).

## Test environments

Preferred progression:

1. fake provider and deterministic fixtures;
2. local simulator or personally controlled hardware;
3. isolated employer/customer laboratory with written authorization;
4. institutional cyber range or industrial control testbed under its rules.

Internet search results and publicly reachable industrial addresses are not
test targets.
