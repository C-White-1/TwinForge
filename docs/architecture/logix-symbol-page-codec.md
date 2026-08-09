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
Live compatibility remains false until the connection adapter is implemented
and validated in a controlled environment.
