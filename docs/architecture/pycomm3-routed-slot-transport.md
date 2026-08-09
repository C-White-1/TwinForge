# pycomm3 Routed Slot Transport

`LivePycomm3RoutedSlotTransport` sends one routed CIP Identity Object request
for an exact slot route. It returns raw `RoutedSlotResult` evidence for the
permission-gated chassis provider.

The default classifier is intentionally conservative:

- CIP success is `populated`;
- an absent response packet or communication failure is `no_response`; and
- every non-zero, unrecognized CIP status is `device_fault`.

The adapter never treats a timeout as an empty slot. `empty` and
`unsupported_route` require an exact `CipSlotStatusSignature` in a named
`CipSlotStatusProfile`. Every signature includes the general status, complete
additional-status tuple, outcome, and a non-empty specification or authorized
fixture reference. Partial and wildcard matches are not supported.

The result retains the raw packet, status words, diagnostic message, profile
name, source reference, and whether a signature matched. This allows a profile
to be reviewed or replaced without losing the original evidence.

Tests replace `CIPDriver` and open no sockets. The example signatures in tests
are synthetic contract fixtures; they are not shipped as Rockwell defaults.
