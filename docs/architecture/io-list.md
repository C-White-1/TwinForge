# I/O List

TwinForge builds a vendor-neutral channel schedule from modeled module
capability and explicit local-I/O aliases. It does not derive physical wiring
from a tag name or assume that an unreferenced terminal is electrically unused.

## Channel evidence

Each known physical channel retains its chassis, slot, module, catalog number,
vendor, signal type, direction, normalized member, source operand, assigned
tags, descriptions, engineering unit, range, and capability source.

The assignment status is one of:

- `assigned` when one or more explicit aliases target the channel;
- `spare` when the modeled channel has no explicit alias assignment; or
- `unavailable_by_configuration` when the module capability says the nominal
  channel exists but the captured configuration does not make it available.

A spare is therefore a review candidate, not proof of spare field wiring. For
example, wiring modes may reserve or combine terminals in ways not represented
by a simple channel count.

## Unresolved evidence

Explicit `Local:` aliases that cannot be decoded or matched to a modeled
physical channel are retained separately. TwinForge does not silently discard
them or manufacture a module capability.

## Report formats

The `twinforge report` bundle writes `io_list.md`, `io_list.csv`, and
`io_list.json`. These deterministic files are intended for engineering review,
data exchange, and regression comparison.
