# CIP Controller Enrichment

TwinForge composes routed CIP Identity discovery and explicitly planned
controller metadata through `MetadataEnrichedControllerProvider`.

The provider is a decorator. It leaves the Identity provider responsible for
the standard CIP Identity Object and delegates each additional object read to
`PermittedControllerMetadataExecutor`. It then lowers decoded metadata into
the vendor-neutral controller observation while retaining every raw object
reply as evidence.

## Safety boundary

Before the first transport request, the decorator verifies that:

- the metadata target and route match the requested controller;
- the operator permit authorizes the exact route;
- every requested decoder is registered;
- the metadata executor has not already consumed its one-shot plan; and
- the combined request budget is declared in the routed capture plan.

Preflight performs no transport I/O. A failure therefore prevents the
Identity request as well as all metadata requests.

Vendor-specific plans may name only one vendor ID. After the standard Identity
read, the decorator compares that required vendor with the observed Identity
vendor. A mismatch stops execution before any vendor-specific object request.
The Identity request is deliberately the only request needed to make this
decision.

## Request budgets

Each controller read declares one Identity request. Its optional metadata
plan declares one request budget per allowlisted object request. The routed
capture total is the sum of both values, so adding enrichment cannot silently
increase network activity.

## Evidence and portability

Only specification-attributed requests and registered decoders can populate
vendor-neutral metadata fields. Unknown payloads, additional CIP status words,
raw replies, and failed object reads remain attached as object evidence. This
keeps vendor-specific details out of the core model without discarding them.

The packet-level integration fixture uses a fake `pycomm3` driver. It proves
the complete composition boundary without connecting to a controller. Live
validation and further vendor-specific request profiles remain controlled-lab
work.
