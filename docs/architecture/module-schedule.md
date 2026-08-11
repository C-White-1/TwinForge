# Module and Spare-I/O Schedule

The module schedule combines the complete modeled module inventory with the
channel-level I/O list. It includes controller, communication, nested, and I/O
modules even when no channel capability has been established.

## Capacity states

For modules with modeled capability, the schedule reports nominal and
configured channel counts together with assigned, spare-candidate, and
configuration-unavailable totals.

For other modules, capability is `unknown`; TwinForge does not convert missing
evidence into zero capacity. This distinction is important for controllers,
communication adapters, third-party devices, and unfamiliar I/O catalogs.

Spare candidates mean that no explicit software alias assignment was observed.
They still require physical wiring and module-configuration review because
wiring modes may reserve or combine terminals.

## Report formats

The `twinforge report` bundle writes `module_schedule.md`,
`module_schedule.csv`, and `module_schedule.json`. Each row also retains module
identity, parentage, inhibition, connection-loss behavior, keying, and the
capability evidence source when available.
