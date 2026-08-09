# Bounded pycomm3 Identity Adapter

TwinForge's first live CIP adapter deliberately exposes a narrow evidence
boundary. It performs one unconnected Identity Object
`Get_Attributes_All` request for each explicitly allowlisted private IPv4
target.

This first adapter does not broadcast, scan address ranges, traverse CIP
routes, enumerate chassis slots, read tags, or expose a live-discovery CLI
command. Its default timeout is two seconds and its hard maximum is ten
seconds. A provider instance permits exactly one request per target.

Both decoded Identity Object attributes and the raw reply evidence are
retained. The transport is injectable, so decoder, authorization, and request
budget tests run without opening network sockets.

Live use remains deferred until an operator-confirmation workflow and a
controlled-laboratory verification fixture are available.

## Controlled-laboratory configuration

The adapter does not require subclassing or source-code overrides for a normal
laboratory test. The operator must explicitly supply the authorized targets,
the authorization evidence, and, only when necessary, a timeout override.

Before enabling a live test:

1. Use an isolated or otherwise controlled network owned by the operator.
2. Record the laboratory authorization or change-reference identifier.
3. Confirm every device IP address independently; do not derive an address
   range for scanning.
4. Permit outbound TCP port 44818 from the TwinForge host to only those
   devices, where host or laboratory firewall rules are used.
5. Start with one non-production target and the default two-second timeout.
6. Confirm that the expected device identity was returned before adding
   another target.

The following example shows the configuration that will be required once the
operator-confirmation workflow is available:

```python
from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryScope,
    DiscoveryTarget,
    Pycomm3CipIdentityProvider,
    capture_snapshot,
    cip_identity_plan_json,
    plan_cip_identity_capture,
    snapshot_json,
)

targets = (
    DiscoveryTarget(
        address="192.168.10.20",
        label="Authorized lab controller",
    ),
)

scope = DiscoveryScope(
    engagement="TwinForge controlled CIP laboratory",
    authorization_reference="LAB-CHANGE-001",
    targets=targets,
    operations=(DiscoveryOperation.CIP_IDENTITY,),
)

# This is socket-free. Review it before constructing the live provider.
plan = plan_cip_identity_capture(scope, timeout=2.0)
print(cip_identity_plan_json(plan))

provider = Pycomm3CipIdentityProvider(
    allowed_targets=targets,
    timeout=2.0,
)

snapshot = capture_snapshot(scope, provider)
print(snapshot_json(snapshot))
```

Replace the example IP address, label, engagement, and authorization reference
with laboratory-specific values. Passing a different `timeout` overrides the
two-second default, but the value must remain greater than zero and no more
than ten seconds. Increasing the timeout does not increase the request budget:
each provider instance still permits only one request per allowlisted target.

For several devices, add each exact `DiscoveryTarget` to `targets`. The same
tuple must be supplied to both `DiscoveryScope` and
`Pycomm3CipIdentityProvider`; this makes the authorized scope and the network
adapter allowlist independently enforce the same boundary.

## Identity-only baseline and future overrides

The current implementation is an endpoint Identity adapter, not the finished
controller-discovery feature. Its immediate value is to prove authorization,
request budgeting, raw-evidence capture, identity decoding, and reconciliation
with offline L5X modules before broader reads are enabled.

A useful controller inventory will also require explicit, independently
authorized overrides of that Identity-only baseline:

| Capability | Authorization boundary | Evidence |
| --- | --- | --- |
| Route traversal | Exact route and depth | Identity and route |
| Chassis inventory | Route and slot range | Slot and module identity |
| Controller metadata | Metadata operation | Properties and attributes |
| Software inventory | Catalog operation | Programs, tasks, and routines |
| Tag inventory | Metadata operation and scope | Definitions without values |
| Runtime values | Value approval and tag list | Values and timestamps |

These are planned capability profiles, not reasons to weaken the existing
provider. They should be implemented through separate operations and bounded
providers so an operator can authorize chassis discovery without implicitly
authorizing tag-value reads. `CipRouteDeclaration` now represents an exact,
typed path and its maximum depth without opening a socket. The Identity
provider continues to reject routed targets; a future routed provider will
consume these declarations.

The future laboratory configuration should therefore make the authorized
operations conspicuous. The following is illustrative design, not currently
executable API:

```python
operations = (
    "cip_identity",
    "cip_chassis_inventory",
    "cip_controller_metadata",
    "cip_software_catalog",
    "cip_tag_metadata",
)

route_policy = {
    "route": (1, 0),
    "slot_range": range(0, 17),
    "maximum_route_depth": 2,
}

runtime_value_policy = {
    "enabled": False,
    "allowed_tags": (),
}
```

Before those profiles become available, each requires:

1. a distinct `DiscoveryOperation` value;
2. a specification-backed evidence contract that preserves unknown data;
3. an exact target, route, slot, or tag allowlist as applicable;
4. per-operation and total capture request budgets;
5. a dry-run summary and explicit operator confirmation;
6. tests using an injected transport; and
7. verification in an authorized controlled laboratory.

## Safeguards that remain independent of capability

Broader authorized discovery should not remove the safeguards against:

- public IP addresses or DNS hostnames;
- IPv6 targets;
- subnet or address-range scanning;
- broadcast List Identity requests;
- undeclared routes, slots, controllers, programs, or tags;
- runtime-value reads implied by metadata authorization; or
- requests beyond the declared per-operation and total budgets.

Do not remove or bypass checks in `Pycomm3CipIdentityProvider` locally to gain
the planned capabilities. Doing so would make the laboratory configuration
unrepeatable and unaudited while also mixing unrelated responsibilities into
the Identity adapter.
