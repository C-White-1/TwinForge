# Logix Symbol Page Codec

TwinForge contains an offline codec for one Logix Symbol Object
`Get_Instance_Attribute_List` response. It does not open a controller
connection.

The request contract records Symbol Object class `0x6B`, service `0x55`, the
starting instance and the exact attribute allowlist. The current attribute set
matches the inspected `pycomm3 1.2.16` implementation:

- symbol name;
- symbol type;
- symbol address;
- symbol object address;
- software control;
- three array dimensions; and
- external access when supported by the controller revision.

The response codec accepts success and partial-transfer statuses. Every decoded
record retains its complete raw record bytes and numeric attributes. A partial
page derives the next starting instance from the last returned instance. An
empty partial page, malformed record or other CIP status fails explicitly.

Known symbol-name prefixes lower into structural inventory items:

- `Program:` becomes a program;
- `Routine:` becomes a routine under the enumerated program scope;
- `Task:` becomes a task; and
- other symbols become tag definitions.

The caller's capability allowlist controls which lowered items leave the codec.
All decoded source records remain available even when a capability is not
selected. Runtime tag values are never requested or represented.

This codec is the packet-fixture foundation for a future live page transport.
`ExperimentalPycomm3LogixSymbolTransport` now connects the codec to public
`LogixDriver` construction and `generic_message`. It disables pycomm3's
automatic tag initialization and issues exactly one connected request per
executor page. Its opaque state moves from controller enumeration into each
discovered program scope without repeating the controller upload.

The transport requires a non-empty laboratory evidence reference and remains
explicitly experimental. Packet fixtures prove request sequencing, route-path
construction, partial transfer, program-scope traversal and evidence capture;
they do not constitute live controller validation.

## Command line

`twinforge discover software` writes a dry-run plan by default. The caller must
provide the target, every `PORT/LINK` route segment, authorization reference,
capability allowlist and maximum request count.

Live traffic requires the additional `--execute-experimental` switch together
with `--confirmed-by`, a timezone-qualified `--confirmed-at`, and
`--laboratory-evidence-reference`. Omitting any of them fails before transport
construction. An output path is optional; without one, JSON is written to
standard output.
