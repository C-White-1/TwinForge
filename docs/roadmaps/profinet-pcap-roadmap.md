# PROFINET PCAP analysis roadmap

## Objective

Add offline, evidence-preserving analysis of lawfully obtained PROFINET packet
captures. The first capability should inventory protocol families and qualify
whether a capture contains sustained cyclic PROFINET RT evidence. Later work
may calculate per-stream timing observations and correlate them with GSDML and
the neutral communication model.

This is an offline analysis roadmap. It does not authorize live capture,
packet replay, frame injection, PROFINET configuration, or control actions.

## Evidence boundary

A file labelled “PROFINET” may contain only DCP discovery, LLDP topology, RPC
configuration, or a few isolated frames. Such a file can test decoding but
cannot support claims about cyclic jitter or telegram gaps.

Timing analysis requires, at minimum:

- sustained PROFINET RT traffic, normally Ethernet type `0x8892`;
- packet timestamps with recorded resolution;
- enough consecutive frames to establish an observed cycle distribution;
- both traffic direction and capture-point information where available;
- disclosure of TAP, SPAN, host, adapter, and capture-tool limitations; and
- explicit handling of capture loss before classifying a missing telegram.

A missing captured frame is not automatically a missing network telegram. A
SPAN port, capture adapter, operating system, or recorder may itself drop the
frame. TwinForge must report this uncertainty rather than silently presenting
capture loss as device degradation.

## Phase 1: lawful corpus admission

- [ ] Define a versioned PCAP corpus manifest containing source URL, title,
  acquisition date, copyright or licence, SHA-256, size, capture format,
  sanitization state, and permitted use
- [ ] Record capture-point, timestamp-resolution, interface, and known packet
  loss evidence when supplied
- [ ] Enforce configurable file-size and packet-count limits before parsing
- [ ] Reject unsupported or malformed capture containers without partial
  promotion
- [ ] Keep third-party captures beneath ignored `reference/PROFINET/PCAP/`
  until redistribution and sensitivity review permits a smaller fixture
- [ ] Add only independently authored or explicitly redistributable sanitized
  captures to automated tests

Candidate sources and their limitations are recorded in
[PROFINET PCAP sources](../references/profinet-pcap-sources.md).

## Phase 2: container and protocol qualification

- [ ] Parse classic PCAP and PCAPNG container metadata without network access
- [ ] Preserve raw packet bytes or exact source offsets for lossless review
- [ ] Inventory Ethernet, VLAN, LLDP, DCP, MRP, PTCP, PNIO RPC, PROFINET RT,
  and unknown frame counts
- [ ] Identify `0x8892` streams by source MAC, destination MAC, VLAN, Frame ID,
  and direction without inventing device identities
- [ ] Classify each capture as discovery-only, configuration-bearing,
  cyclic-bearing, timing-qualified, or unsupported
- [ ] Export deterministic JSON and Markdown qualification reports
- [ ] Cross-check a curated subset with pinned `tshark` output while keeping
  the TwinForge result independent of a locally installed GUI

## Phase 3: cyclic timing observations

- [ ] Extract frame sequence or cycle evidence only where the decoded frame
  form establishes its meaning
- [ ] Calculate observed inter-arrival minimum, maximum, median, percentiles,
  and deviation from the observed nominal cycle
- [ ] Report suspected gaps separately from confirmed capture discontinuities
- [ ] Detect timestamp discontinuities, reordered frames, duplicated frames,
  truncated packets, and recorder loss indicators
- [ ] Keep thresholds as explicit user input or documented device evidence;
  do not invent universal “good” jitter limits
- [ ] Preserve every excluded or undecodable frame as diagnostic evidence

## Phase 4: semantic correlation

- [ ] Parse GSDML device, module, submodule, parameter, and diagnostic
  definitions through a lossless source boundary
- [ ] Correlate observed MAC, station-name, IP, Frame ID, slot, and subslot
  evidence only when matches are unique
- [ ] Represent monitoring equipment separately from the devices it observes
- [ ] Link qualified observations to neutral communication endpoints and
  AutomationML interfaces
- [ ] Support permanent-observer sources such as Agent Blond through
  profile-specific adapters without placing vendor fields in the core model

## Phase 5: operational reporting

- [ ] Produce per-device communication-quality summaries with provenance and
  confidence
- [ ] Compare accepted captures over time without erasing superseded evidence
- [ ] Distinguish commissioning baselines, transient findings, persistent
  degradation, and capture-quality limitations
- [ ] Export PLC/HMI alarm candidates only as engineering recommendations,
  never as automatically deployed control logic

## Explicit non-goals

- Replaying captured PROFINET frames.
- Crafting DCP, RPC, cyclic, alarm, or configuration traffic.
- Scanning live networks as part of offline PCAP analysis.
- Treating passive observations as proof of physical-device identity.
- Claiming safety, availability, or predictive-maintenance guarantees from
  packet timing alone.

## First implementation slice

The first code milestone should implement the corpus manifest and bounded
container qualification. It should answer, deterministically:

1. Is this a structurally valid PCAP or PCAPNG file?
2. What capture interfaces and timestamp properties are recorded?
3. Which Ethernet and PROFINET protocol families are present?
4. Does it contain enough sustained `0x8892` traffic to justify later timing
   analysis?
5. What evidence remains unknown, truncated, unsupported, or unsuitable?

No jitter or telegram-gap conclusion should be emitted in that first slice.
