# CIP Controller Evidence

`CipControllerObservation` is the vendor-neutral evidence boundary for future
controller discovery. It combines an observed CIP identity with an optional
explicit route and metadata that has actually been reported by the device.

The generic metadata fields are deliberately small:

- logical controller name;
- project name and revision;
- firmware revision; and
- operating mode.

Missing metadata remains `None`; TwinForge does not infer it from a catalog
number or an offline project. Vendor-specific attributes remain in
`raw_attributes`. Every object read can also retain its class, instance,
attribute, service, status words, request payload, response payload, and
decoded evidence through `CipObjectEvidence`.

The recursive `JsonEvidence` value permits unknown structured attributes to be
preserved without adding vendor-specific fields to the core model. Raw bytes
must be represented as hexadecimal text so evidence remains deterministic and
JSON-compatible.

`CipControllerDiscoveryProvider` defines the future live or fixture-provider
boundary. This milestone does not implement that provider, issue CIP requests,
or mark the routed controller-read roadmap item complete.
