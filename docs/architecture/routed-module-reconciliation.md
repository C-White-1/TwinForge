# Routed Module Reconciliation

TwinForge compares converted L5X modules with discovered chassis modules only
through explicit `RoutedConfiguredModuleBinding` records. Each binding names:

- the configured-module evidence key;
- the complete declared chassis route key;
- the non-negative chassis slot; and
- the converted vendor-neutral module.

Module names, IP addresses, catalog-number suffixes, and parent names never
create bindings implicitly. This matters because every slot behind a chassis
gateway shares the same discovery target address.

## Comparison

A populated bound slot reuses the existing field comparison for vendor ID,
device type, product code, and revision. A custom EKey identity is compared
independently. Results remain exact, partial, conflicting, or insufficient.
Each candidate also carries a separate specification-backed electronic-key
evaluation, so ordinary identity comparison is never mistaken for a keying
decision. Compatible Module remains deferred to the device and product family.

Every candidate includes an evidence reference containing the complete route
key and slot number. Raw routed observations remain in the discovery snapshot.

## Unresolved evidence

Reconciliation retains an issue when:

- a bound route or slot was not observed;
- the bound slot was empty, unresponsive, unsupported, or faulted; or
- a populated discovered slot had no explicit L5X binding.

These outcomes are not converted into mismatches. They represent different
evidence conditions and remain available for operator review.

## Approved topology mappings

`apply_chassis_module_mapping_reviews` provides the explicit boundary between
routed reconciliation and the vendor-neutral core model. An accepted review
must identify the existing controller, chassis, and module asset IDs and is
joined back to the original explicit binding to recover its route and slot.
The review retains its operator, timezone-aware timestamp, rationale, and
comparison evidence.

Conflicting or insufficient comparisons require an explicit conflict override.
An electronic-key rejection also requires that override; it is never silently
treated as compatible. Rejected and deferred reviews cannot name core assets.
One module asset cannot be mapped twice, and a chassis asset cannot acquire
conflicting controller parents within a review operation.

The result is a deterministic staging document. It does not construct, mutate,
or reparent `Controller`, `Chassis`, or `Module` instances. Applying approved
mappings to a repository remains a separate transactional responsibility.
