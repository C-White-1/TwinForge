# SNMP Request Safety Policy

TwinForge applies one immutable `LoopbackSnmpPolicy` to SNMPv2c and SNMPv3
laboratory captures. The policy is validated before any network operation.

## OID allowlist

Every walk starts from an explicitly configured root. Roots must be unique,
canonical dotted numeric OIDs; symbolic names, empty components, leading
zeros, and duplicate roots are rejected. PySNMP is instructed not to walk
lexicographically beyond each root.

The default allowlist covers only the system, interface, legacy address,
Bridge MIB, ENTITY-MIB, and LLDP evidence currently understood by TwinForge.
Supplying a different tuple replaces that list explicitly; it does not enable
an unrestricted tree walk.

## Independent bounds

The policy enforces all of the following:

- a positive transport timeout;
- a non-negative retry count;
- a total unique-varbind ceiling across all roots;
- a separate response ceiling, preventing duplicate or empty responses from
  evading the varbind budget; and
- a positive delay after every received walk response, pacing successive
  requests made by the asynchronous walker.

Exhausting either budget raises a structured `DiscoveryProviderError` and
stops the capture. Partial observations are not returned as if the capture had
completed normally.

## Scope boundary

These controls complement, rather than replace, the adapter's literal
loopback-address restriction and the engagement authorization recorded by the
discovery scope. Increasing a limit or changing the allowlist does not grant
authority to query another endpoint.
