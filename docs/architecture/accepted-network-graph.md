# Accepted Network Graph

TwinForge lowers accepted SNMP topology evidence into an
`AcceptedNetworkGraph`. This is an assembly-stage aggregate: it joins durable
assets, exactly observed interfaces, and operator-accepted neighbour links
without changing the vendor-neutral core model or inventing connectivity.

## Inputs

Lowering requires:

- the immutable discovery snapshot containing SNMP interface evidence;
- the topology-correlation result containing observed node identities;
- the topology-acceptance result containing reviewed relationships; and
- an explicit mapping from durable asset keys to vendor-neutral assets.

The caller also supplies the identity, name, and protocol of the resulting
vendor-neutral `Network`.

## Evidence boundary

Only relationships in `accepted_relationships` become graph links. Every link
is labelled `operator_accepted` and retains its original evidence references.
Rejected, deferred, and unreviewed candidates are not lowered.

For graph nodes participating in accepted relationships, TwinForge retains all
interfaces exactly reported in the corresponding SNMP observations. An
accepted relationship that identifies a source interface must resolve to one
of those observations. Missing assets, topology nodes, or referenced
interfaces cause lowering to fail instead of producing a guessed graph.

Forwarding-database observations do not become direct links merely because two
addresses appear together. Any such relationship must first pass through the
normal correlation and operator-acceptance boundary.

## Why this is a staging aggregate

The core `Network` and `Asset` types intentionally remain small and
vendor-neutral. SNMP indices, operational states, raw addresses, and evidence
provenance belong to the assembly result until a broader, protocol-neutral
interface model is justified by multiple sources and targets. Lowering
therefore does not mutate assets or attach SNMP-specific metadata to them.

The deterministic JSON representation is suitable for review, testing, and a
future exporter. It is not a claim that every observed interface or accepted
neighbour has already been promoted into the persistent domain model.
