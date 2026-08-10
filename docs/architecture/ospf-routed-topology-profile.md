# OSPF Routed-Topology Profiles

TwinForge reserves OSPF MIB evidence for a distinct routed-topology phase. It
is not part of baseline asset, interface, or physical-neighbour discovery.

## Profiles

Two optional, evidence-only profiles are defined:

- `ospfv2-routed-topology` uses the OSPFv2 MIB root
  `1.3.6.1.2.1.14`, standardized by
  [RFC 4750](https://www.rfc-editor.org/rfc/rfc4750); and
- `ospfv3-routed-topology` uses the OSPFv3 objects root
  `1.3.6.1.2.1.191.1`, standardized by
  [RFC 5643](https://www.rfc-editor.org/rfc/rfc5643).

Both profiles are disabled by default and excluded from the baseline OID
allowlist. TwinForge's adapter remains read-only and never changes writable
OSPF configuration objects.

## Relationship semantics

An OSPF neighbour or link-state relationship describes routing-protocol
adjacency and reachability. It does not prove:

- a direct physical cable;
- a shared Ethernet segment with only two endpoints;
- asset ownership;
- a PLC I/O relationship; or
- the route selected for every application flow.

Virtual links, tunnels, routed VLAN interfaces, redundancy, and dynamic
protocol state can all separate logical adjacency from physical topology.
OSPF evidence must therefore use routed relationship types rather than the
existing LLDP physical-neighbour candidate.

## Security and authorization

OSPF MIBs expose operationally sensitive router identifiers, areas,
interfaces, neighbours, and link-state information. An authorized scope must
opt in explicitly, use a read-only SNMPv3 principal with `authPriv`, and apply
the normal OID, timeout, response, varbind, and pacing limits.

## Deferred lowering

Semantic lowering remains deferred until the routed-topology model defines:

- routers, areas, interfaces, neighbours, and virtual links;
- OSPFv2 and OSPFv3 identifier differences;
- point-in-time protocol state and discontinuities;
- evidence provenance for link-state database records; and
- reconciliation with accepted physical topology and configured networks.

Until that phase, explicitly captured OSPF values remain raw evidence. They do
not create network links, accept relationships, or mutate durable assets.
