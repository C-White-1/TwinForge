# CIP Chassis Evidence

TwinForge plans chassis discovery with an explicit slot allowlist rather than
probing until a device stops responding. `CipChassisSlotPlan` binds that list
to an authorized `CipRouteDeclaration` and states both the per-slot and total
request budgets before any future transport is constructed.

Every requested slot must produce exactly one evidence outcome:

- `populated`, with required CIP Identity evidence;
- `empty`;
- `no_response`;
- `unsupported_route`; or
- `device_fault`.

These states must not be collapsed. An empty slot is observed configuration,
while no response is incomplete evidence. Unsupported routing and a device
fault have different remediation paths and may carry different CIP status
words.

Unknown or vendor-specific attributes remain in `raw_attributes`. Raw response
payloads, general status, and additional status words are retained alongside
the interpreted state. A complete chassis observation must account for every
planned slot, preventing failed reads from disappearing silently.

`CipChassisDiscoveryProvider` is an offline provider boundary only. No routed
transport or chassis request is implemented by this milestone.
