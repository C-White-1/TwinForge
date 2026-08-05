# Discovery Topology Correlation

TwinForge keeps observed protocol evidence separate from accepted network
topology. Correlation produces candidates that can be reviewed, reconciled
with other sources, or lowered into the vendor-neutral model later.

## Evidence meanings

### LLDP remote-system evidence

An LLDP remote-system row supports a `reported_neighbour` relationship. It
means that the observed agent reported a neighbour on one of its LLDP local
ports. The row may be stale, duplicated, incomplete, or ambiguously mapped to
an interface, so the relationship remains a candidate.

LLDP local-port numbers are not assumed to equal SNMP `ifIndex`. TwinForge
sets `source_interface_index` only when explicit local-port evidence resolves
the relationship.

### Bridge forwarding evidence

A forwarding-table row supports `mac_reachability`. It means that a bridge
learned a MAC address through a bridge port. The MAC might belong to a directly
attached device or to any device behind another switch, access point, virtual
switch, or shared segment. It is therefore not described as a physical link.

Bridge-port numbers are not assumed to equal `ifIndex`. TwinForge uses the
Bridge MIB base-port mapping when it is present and otherwise preserves an
unresolved interface.

### Corroboration

An LLDP relationship becomes `corroborated` when a forwarding entry reports
the same chassis MAC through the same explicitly resolved interface. This adds
independent evidence but does not convert the candidate into unquestioned
truth.

## Confidence vocabulary

- `indirect`: reachability or another non-neighbour observation
- `protocol_reported`: a neighbour relationship directly reported by LLDP
- `corroborated`: compatible evidence from more than one observation family

These values are qualitative evidence classes, not statistical probabilities.

## Identity correlation

An LLDP management address resolves to a scoped discovery target only when it
matches exactly one known target address. Otherwise, the candidate retains a
chassis-derived identity. Names alone are retained as labels and are not used
as unique identity evidence.

## Lowering boundary

`TopologyCorrelationResult` is intentionally outside the core `Network` and
`Connection` model. A future acceptance policy may lower reviewed candidates
into that model using requirements such as:

- minimum confidence class;
- freshness limits;
- agreement between SNMP, CIP, L5X and operator-supplied evidence;
- ambiguity resolution; and
- explicit retention of source observations and correlation decisions.

Until that policy exists, topology candidates remain analysis output rather
than asserted plant configuration.
