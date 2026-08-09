# CIP Software Inventory Policy

TwinForge treats controller structure and runtime tag values as different
operations with different authorization boundaries.

`CipSoftwareInventoryPlan` permits only structural enumeration capabilities:

- programs;
- routines;
- tasks; and
- tag definitions.

It contains an explicit maximum request count and always serializes
`runtime_values_permitted` as `false`. Supporting tag definitions therefore
does not authorize reading a tag's current value.

`CipRuntimeValueReadPlan` is a separate dry-run contract. It requires another
runtime-value approval reference, a justification, an explicit list of tag
paths, and a request budget large enough to cover those paths. It cannot be
created implicitly from a software-inventory plan.

Neither plan performs network I/O. Provider capability negotiation, paginated
enumeration, evidence capture, and runtime-value execution remain later
milestones. Default inventory reports must consume structural observations,
not runtime-value captures.
