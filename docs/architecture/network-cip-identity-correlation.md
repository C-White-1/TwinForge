# Network and CIP Identity Correlation

TwinForge correlates SNMP-derived topology nodes with CIP Identity Object
observations without merging either source or claiming that indirect network
evidence is a physical connection.

## Accepted match paths

`correlate_network_nodes_with_cip_identities` recognizes only these retained
evidence paths:

- `scoped_target`: the topology node and CIP identity use the same complete
  discovery-target key, including any route;
- `management_address`: a topology address matches exactly one scoped CIP
  identity target address; and
- `observed_interface_mac`: a topology chassis or forwarding-table MAC matches
  an interface MAC observed by SNMP on a target that also produced a CIP
  identity.

The result records every applicable basis. A match is labelled
`cross_layer_corroborated`, while the original CIP, SNMP, LLDP, and forwarding
observations remain unchanged.

## Ambiguity and non-evidence

If the evidence produces zero or multiple candidate CIP identities, the node
is retained in `unresolved_topology_node_keys`. TwinForge does not choose the
first candidate.

Names, product descriptions, vendor assumptions, subnet proximity, and MAC
vendor prefixes are not identity evidence. A forwarding-table MAC can resolve
to an identity only through an independently observed interface MAC; the FDB
row alone still expresses indirect reachability rather than a physical link.

This correlation result remains upstream of topology review and the accepted
network graph. It can help an operator understand an endpoint, but it does not
automatically accept a relationship or promote a durable asset.
