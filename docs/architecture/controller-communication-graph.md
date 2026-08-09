# Controller Communication Graph

TwinForge builds a multi-controller graph from configured Logix `MESSAGE` tag
evidence in an `L5XCorpus`. This is a graph of configured communication intent,
not proof that messages executed or network traffic occurred.

Each `ConfiguredMessageEvidence` retains:

- its source controller workspace and source file;
- controller or program ownership;
- the exact tag name;
- message type;
- configured connection path; and
- configured destination tag.

The evidence key includes the workspace, source path, owner, and tag. This keeps
same-named message tags in different programs, files, or controllers distinct.

## Explicit destination binding

Connection-path text is not interpreted as a controller identity. A
`ControllerCommunicationBinding` must map the exact message evidence key to an
existing target workspace key. Unknown evidence, unknown workspaces, and
duplicate bindings fail validation. Messages without a binding remain in
`unbound_messages`; they are never discarded or turned into guessed edges.

Multiple messages between the same source and target are grouped into one
directed edge while retaining every evidence record. All corpus workspaces are
represented as nodes, including provisional context-only workspaces, and the
`confirmed` field preserves that distinction.

## Interpretation boundary

An edge means only that an operator-approved corpus binding associates a
configured message with another controller workspace. It does not establish:

- successful runtime communication;
- packet direction observed on a network;
- message frequency or last execution time;
- target availability; or
- equivalence between the workspace and a discovered physical asset.

Runtime capture, network observations, and durable asset reconciliation remain
separate evidence sources that may corroborate this graph later.
