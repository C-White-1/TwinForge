# pycomm3 Controller Metadata Transport

`LivePycomm3MetadataTransport` translates one approved metadata request into a
routed `pycomm3` generic message. It uses UCMM Unconnected Send and the exact
two-byte-padded route produced by the route translation boundary.

The transport does not choose object numbers, infer metadata semantics, or
decode vendor objects. Those responsibilities remain in the metadata plan and
registered decoder layers.

Both successful and failed response packets preserve:

- the CIP general status;
- every additional 16-bit status word;
- the response payload after the status section;
- the complete raw reply; and
- the `pycomm3` diagnostic message.

Malformed or absent packets become provider errors rather than fabricated
status values. `standard_metadata_decoders` currently exposes only a
specification-backed CIP Identity firmware-revision decoder. Vendor-specific
decoders require documented or controlled-fixture evidence.

Tests replace `CIPDriver` with packet-shaped fixtures and verify the complete
generic-message argument set. They open no sockets. Live laboratory validation
remains pending.
