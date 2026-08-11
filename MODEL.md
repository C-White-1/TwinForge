# Domain model

```text
Plant
└── Controller
    ├── Identity
    ├── Chassis
    │   └── Module
    │       ├── Identity and ElectronicKey
    │       ├── Connections
    │       ├── EngineeringUnitEvidence
    │       ├── EngineeringRangeEvidence
    │       └── ModuleCapability
    ├── Datatypes
    ├── Tags
    │   ├── initial scalar value
    │   ├── ordered composite initial-value tree
    │   ├── engineering unit/range
    │   └── source extensions
    ├── Programs
    │   ├── program tags
    │   └── Routines
    │       └── LadderRungs
    └── Tasks
        └── scheduled Program references
```

## Evidence and provenance

TwinForge distinguishes explicit, derived and inferred information.

- Module-channel units are explicit L5X evidence.
- Alias tags inherit unit/range evidence from module channels.
- Numeric comparison operands may inherit derived engineering units.
- Description suffixes are lower-confidence inferred evidence.
- Module capacity decoded from recognized catalog conventions records its
  source.
- Unknown or conflicting evidence is preserved and diagnosed.

## Tag initial values

Scalar decorated values remain available through `Tag.initial_value` for
setpoint reporting and target exporters. Structured and array decorated values
use `Tag.composite_initial_value`, an ordered tree of structures, members,
arrays, indexed elements, and typed scalar leaves.

Composite nodes retain their source node kind and raw attributes as provenance.
The tag source extension remains the authoritative lossless representation;
typed promotion adds navigation without replacing or rewriting that evidence.

## I/O state

Module capability separates:

- nominal hardware capacity;
- configured channel count;
- unavailable-by-configuration count;
- alias and direct-RLL assignments; and
- usable unassigned points reported as spares.

Physical `Channel` and CIP `Assembly` entities remain deferred until sufficient
module-profile or live CIP evidence is available.
