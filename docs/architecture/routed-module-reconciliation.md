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
