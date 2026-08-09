# CIP Controller Metadata Capture

`PermittedControllerMetadataExecutor` executes a previously validated metadata
plan through an injected transport. Before the first request, it verifies the
operator permit, authorization reference, exact route, decoder registry, and
whole-plan request budget.

Only successful responses with an explicitly registered decoder can populate
a vendor-neutral controller field. Semantic fields accept text values; a type
mismatch is reported rather than coerced. A plan cannot map two requests to the
same semantic field, avoiding implicit precedence between conflicting sources.

Every response becomes `CipObjectEvidence`, including failed requests. Class,
instance, attribute, service, general status, additional status, response
payload, raw reply, diagnostic message, and decoded evidence are retained.
Unknown and failed responses therefore remain available for later analysis.

`apply_controller_metadata` merges decoded values only when the target and
route match the original controller observation. Existing fields remain
unchanged when a response fails or has no decoder.

The transport is injectable and current tests open no sockets. A live pycomm3
metadata transport remains a separate adapter milestone.
