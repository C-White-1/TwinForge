# Electronic-Key Evaluation

TwinForge evaluates electronic keying separately from ordinary configured and
discovered identity comparison. A field match is evidence; it is not
automatically proof that a device family will establish a connection.

The evaluator uses the five CIP keying attributes retained by the L5X and CIP
Identity models:

- vendor ID;
- device type;
- product code;
- major revision; and
- minor revision.

The L5X modes and fields are defined by Rockwell Automation publication
`1756-RM014D-EN-P`, September 2025. Compatibility behavior is based on
publication `LOGIX-AT001A-EN-P`, September 2014.

## Verdicts

`ExactMatch` has a definitive evidence result. All five attributes must be
available and equal for `satisfied`; a conflict produces `rejected`, and a
missing configured attribute produces `deferred`.

`Disabled` produces its own `disabled` verdict. This means the keying
attributes are not used for the connection attempt. It is not a declaration
that the installed device is functionally safe or suitable.

`CompatibleModule` always produces `deferred`. Rockwell documents typical
revision behavior, but the installed device ultimately decides whether it can
emulate the configured device. Product families can implement different rules
and can sometimes accept a different catalog number. TwinForge records a
`typical_compatible_revision` advisory value without converting it into a pass.

The typical revision comparison requires the same vendor, device type, and
product code. It then recognizes:

- the same major revision with the same or a higher minor revision; or
- a higher major revision with any minor revision.

`Custom`, unknown modes, and incomplete evidence also produce `deferred`.
Their comparable fields remain visible, but TwinForge does not invent an
acceptance rule.

## Evidence boundary

Every result names both Rockwell publications and retains matched,
conflicting, and unavailable fields. The evaluator performs no network I/O,
does not alter the model, and does not replace controller or device diagnostics.

Configured and routed module-reconciliation candidates carry this evaluation
as a nested result without replacing their existing identity-comparison status.
Historical manually constructed candidates can omit it, while both maintained
reconciliation paths always populate it.
