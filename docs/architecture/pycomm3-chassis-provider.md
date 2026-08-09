# Permitted pycomm3 Chassis Provider

`CipChassisSlotRouteMap` assigns an exact `CipRouteDeclaration` to every slot
in a bounded chassis plan. The provider does not assume that a slot is always
the final backplane link and does not derive unapproved routes from a catalog
number or chassis size.

Before the first request, `PermittedPycomm3ChassisProvider` verifies:

- the supplied chassis plan matches its configured route map;
- the provider and permit authorization references match;
- every slot route appears in the operator permit; and
- the whole-plan request budget has not already been consumed.

`Pycomm3RoutedSlotTransport` returns a typed `RoutedSlotResult`. The transport,
not the evidence provider, must distinguish populated, empty, no-response,
unsupported-route, and device-fault outcomes. This prevents the provider from
guessing that a timeout represents an empty slot.

The provider preserves route keys, Identity payloads, status words, raw reply
bytes, and unknown vendor attributes. It emits exactly one
`CipChassisSlotObservation` for each planned slot.

The current tests inject a transport and open no sockets. A live transport and
specification-backed status classifier remain pending because captured status
fixtures are needed to distinguish an empty Logix slot from other destination
failures without guessing.
