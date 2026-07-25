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

## I/O state

Module capability separates:

- nominal hardware capacity;
- configured channel count;
- unavailable-by-configuration count;
- alias and direct-RLL assignments; and
- usable unassigned points reported as spares.

Physical `Channel` and CIP `Assembly` entities remain deferred until sufficient
module-profile or live CIP evidence is available.
