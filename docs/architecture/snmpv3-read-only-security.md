# SNMPv3 Read-Only Security

TwinForge represents SNMPv3 User-based Security Model (USM) credentials as
runtime configuration. Authentication and privacy keys are excluded from
representations, discovery snapshots, serialized evidence, and diagnostics.

## Security levels

`SnmpV3SecurityLevel` makes the configured USM level explicit:

- `authPriv` uses SHA-256 authentication and AES-128 privacy and is the secure
  default;
- `authNoPriv` uses SHA-256 authentication without encryption; and
- `noAuthNoPriv` supplies only a username and should be limited to controlled
  compatibility testing.

Credential validation requires exactly the keys applicable to the selected
level. Authentication and privacy passphrases must each contain at least eight
characters when required. Unsupported or contradictory combinations fail
before network activity begins.

## Meaning of read-only

The TwinForge discovery provider exposes only bounded, allowlisted walk
operations and never sends SNMP `SET`. This makes the client behavior
read-only.

SNMP write authority is nevertheless enforced by the managed agent, not by
the client credential object. Production and laboratory agents should assign
the TwinForge USM user to a VACM read view with no write view. Reusing an
administrative USM user would grant that username broader rights even though
TwinForge itself does not exercise them.

## Current adapter boundary

The implemented PySNMP adapter remains loopback-only for the authorized
SNMPSim laboratory. Its target restriction, OID roots, timeout, retry count,
and varbind budget are independent of the USM security level. Extending the
adapter beyond loopback requires a separate authorization and safety boundary;
changing credentials alone does not enable remote discovery.
