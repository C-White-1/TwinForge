# Permitted pycomm3 Routed Identity

`PermittedPycomm3RoutedControllerProvider` is the first controlled routed-read
adapter. It currently reads only the standard CIP Identity Object. Controller
metadata and chassis enumeration remain separate future operations.

The provider requires three independently matching boundaries:

1. an exact provider route allowlist;
2. an attributable `RoutedExecutionPermit` containing the same route key; and
3. the same non-empty authorization reference on the provider and permit.

Without a permit, execution stops before the transport is called. Each provider
instance permits one request per routed controller. The existing private-IPv4
gateway policy, ten-second timeout maximum, and route-encoding validation also
apply.

`LivePycomm3RoutedTransport` sends an unconnected Identity Object
`Get_Attributes_All` request using UCMM Unconnected Send. It consumes the exact
two-byte-padded route form produced by `encode_pycomm3_route`. Response payload
and raw packet evidence are retained with the route key, encoded route,
operation, class, instance, adapter, and adapter version.

Tests replace `CIPDriver` or inject the transport. They verify the complete
request shape and nested response-packet extraction without opening sockets.
Live laboratory verification remains pending.
