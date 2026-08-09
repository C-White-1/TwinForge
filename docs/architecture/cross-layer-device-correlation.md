# Cross-Layer Device Correlation

TwinForge can correlate an assembled software device with an approved routed
module mapping while keeping all three evidence layers distinct:

1. `AssembledSoftwareDevice` proves that a software instance accesses one or
   more configured modules.
2. `RoutedConfiguredModuleBinding` explicitly assigns a configured module to a
   declared route and slot.
3. `AcceptedChassisModuleMapping` records the reviewed routed comparison and
   approved controller, chassis, and module asset IDs.

`correlate_software_devices_with_routed_modules` joins these layers only when
the software assembly and routed binding contain the same in-memory `Module`
object and that binding key has an accepted mapping. Names, catalog-number
suffixes, addresses, slots, and software-provider knowledge do not create a
join.

## Result

Each correlation retains:

- controller workspace, software definition, instance tag, and provider;
- configured-module binding key;
- exact chassis route and slot;
- approved controller, chassis, and module asset IDs;
- software-call evidence; and
- routed discovery evidence.

Software devices without an accepted mapping and accepted mappings without a
software device are both retained explicitly. A software device resolving to
multiple accepted mappings, duplicate accepted binding keys, or multiple
routed bindings for one configured module is rejected as ambiguous.

The result is a reversible evidence link. It does not merge a software device,
configured module, discovered identity, or promoted core asset, and it does not
change ownership in the vendor-neutral model.
