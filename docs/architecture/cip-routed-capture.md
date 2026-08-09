# CIP Routed Capture Orchestration

`CipRoutedCapturePlan` combines explicit controller reads and bounded chassis
slot plans under one engagement and authorization reference. Its total request
budget is calculated before execution from one request per controller plan and
the declared per-slot chassis budgets.

`capture_routed_cip` calls each plan item exactly once in deterministic order.
Expected provider failures become target-specific diagnostics rather than
being mistaken for empty slots or silently discarded. Evidence returned by a
provider must match its plan item; mismatched routes, targets, or slot plans
are rejected as diagnostics.

`FakeRoutedCipProvider` replays controller and chassis fixtures, records every
call, and opens no sockets. It proves the orchestration and provider boundaries
before a live routed adapter is introduced.

`RoutedCipProviderFacade` composes independent controller and chassis providers
without merging their responsibilities. A capture containing only one type of
plan may supply only that provider; requesting a missing capability produces a
target-specific diagnostic.

An end-to-end packet fixture exercises the routed capture, facade, permitted
chassis provider, live slot transport, mocked `CIPDriver`, status profile,
Identity decoder, and final JSON serialization without opening a socket.

The routed snapshot is separate from the original Identity/SNMP snapshot while
the schema is evolving. A later integration milestone can join them without
forcing vendor-specific controller or chassis evidence into the core model.
