# SNMP Physical Asset Candidates

RFC 6933 ENTITY-MIB observations describe physical components reported by an
SNMP agent. TwinForge retains those rows as observations first and lowers them
into reviewable candidates second. It does not create confirmed core assets,
chassis, or modules directly from SNMP evidence.

```text
entPhysicalTable row
        |
        v
SnmpPhysicalEntityObservation
        |
        +--> containment validation findings
        |
        v
SnmpPhysicalAssetCandidate
        |
        +--> SnmpPhysicalContainmentCandidate
        |
        v
future reconciliation and acceptance policy
        |
        v
vendor-neutral core model
```

Every asset candidate retains the observation target, numeric physical class,
available identifying fields, qualitative confidence, and references to the
raw OIDs that support it. The numeric class is preserved instead of being
converted prematurely into a TwinForge asset type.

A containment candidate is emitted only when its reported parent exists in the
same node observation and the child has no containment validation finding.
Root value zero produces no relationship. Missing parents, self-parenting, and
cycles remain explicit findings; the physical rows still produce asset
candidates, but the invalid edges are withheld.

Candidate keys are deterministic within an observation target. They are not
global asset identities and must not be used to merge equipment across
captures without an explicit reconciliation policy. Future acceptance can use
serial numbers, UUIDs, asset IDs, CIP identity, configured modules, and prior
approved inventory as corroborating evidence.

## CIP identity reconciliation

The first reconciliation adapter compares CIP Identity Object observations
with physical candidates reported at the same target. It emits a candidate
only when at least one exact cross-protocol agreement exists:

- product name equals the ENTITY-MIB model, name, or description after only
  case and whitespace normalization; or
- the ENTITY-MIB serial is an all-decimal string exactly equal to the CIP
  numeric serial.

The adapter does not interpret hexadecimal-looking strings, remove model
punctuation, apply manufacturer aliases, or compare records across targets.
Matched fields and the supporting CIP fields and SNMP OIDs are retained as
evidence. Unmatched CIP targets and physical candidates remain explicit in the
result. A match is corroborating evidence, not permission to merge or promote
either observation into the core model.

## Configured-module reconciliation

Converted L5X modules enter reconciliation through an explicit binding between
a configured-module key and an authorized discovery-target key. TwinForge does
not infer that binding from a module name, slot, address, or parent structure.
This is especially important for generic communication modules whose identity
describes the controller-side representation rather than necessarily the
physical endpoint.

The adapter compares the configured module vendor ID, product type, product
code, and complete revision with the discovered CIP Identity Object. It
classifies the comparable evidence as exact, partial, conflicting, or
insufficient. If a converted EKey contains its own identity, those requirements
are compared independently and retain an `electronic_key_identity` prefix.

The identity-comparison status remains distinct from the nested electronic-key
evaluation. Exact Match can produce a definitive keying verdict from complete
identity evidence; Compatible Module, Custom, unknown, and incomplete cases
defer rather than infer vendor behavior. A corroborated SNMP physical candidate
for the same CIP target is linked to the comparison as supporting evidence, not
merged with the configured module.

## Operator acceptance boundary

Candidate acceptance is an auditable staging operation and does not construct
or mutate a core-model `Asset`. Each review records:

- the exact candidate key;
- accept, reject, or defer disposition;
- reviewer identity and timezone-qualified timestamp;
- a non-empty rationale; and
- an operator-supplied durable identity key for accepted candidates.

Several accepted candidates may be grouped under one durable staging identity.
The resulting record retains all candidate keys, observation targets, reviews,
and deduplicated evidence references. This grouping is explicit operator input,
not an automatic identity merge.

Configured-module comparisons marked conflicting or insufficient cannot be
accepted unless the review records `override_conflict`. The override and its
rationale remain on the accepted identity record. Rejected, deferred, and
unreviewed candidates form separate output sets so absence of a decision is
never confused with rejection.

Promotion from a durable staging identity into the vendor-neutral core model
remains a separate future operation.

## Cross-capture lifecycle

Durable staging identities use an append-only lifecycle ledger. The first
accepted observation creates generation 1. A later acceptance using the same
active durable key appends another generation and an observed event. A key
missing from a later capture remains active because temporary network absence,
scope changes, and collection failures are not retirement evidence.

Supersede, merge, and split transitions require explicit operator directives.
Each directive records its sources, targets, actor, timezone-qualified time,
and rationale. Transition targets must have accepted evidence in the current
capture. Sources must be active, cannot transition twice in one advance, and
cannot overlap their targets. A transition cannot predate its latest source
observation or target acceptance.

Transitioned source keys become inactive and cannot later be reused silently.
The ledger retains every generation, complete acceptance reviews, evidence,
and lifecycle event. It still does not create core assets; that final promotion
requires a separate mapping and persistence policy.

## Core promotion

An active durable staging identity can be promoted only through an explicit
operator request. The request supplies the stable core asset ID, display name,
core kind, actor, timezone-qualified time, and rationale. It may also provide
device type, manufacturer, model, and catalogue number when the selected kind
is `Device`. Those values are operator assertions; they are not inferred from
an ENTITY-MIB class or vendor string.

Promotion currently supports generic `Asset` and `Device` objects. It does not
construct `Chassis` or `Module`, because those objects require independently
approved topology, slot, identity, and configuration semantics. Device-specific
fields are rejected for a generic asset.

The promotion record provides the reversible link from the core asset ID to
the durable lifecycle identity. It retains all lifecycle generation numbers,
observation targets, evidence, promotion attribution, and rationale. Promotion
cannot predate the latest generation, target an inactive identity, duplicate a
durable identity or core asset ID within the operation, or conceal a prior
conflict override. A prior override must be acknowledged again at promotion.

The core object itself remains vendor-neutral and the lifecycle ledger remains
unchanged. Persistence into a larger plant or asset repository should validate
the chosen core asset ID against that repository before committing the record.

## Promotion repository boundary

The assembly layer defines an atomic promotion-repository port and an in-memory
reference adapter that can attach newly promoted objects to a `Plant`. The
adapter validates the complete batch before changing repository or plant state.

Repository rules are:

- a durable identity can link to only one core asset ID;
- a core asset ID can link to only one durable identity;
- IDs already present in a plant without a promotion record are collisions;
- replaying the same generations is idempotent;
- updates may only extend the stored generation sequence;
- updates cannot change approved core fields or discard retained evidence; and
- the `Plant` keeps ownership of the original core object during evidence
  updates.

The in-memory adapter is a reference implementation, not durable storage.
`SqlitePromotionRepository` provides the durable, transactional implementation
for multiple processes or application instances sharing one database file. It
uses `BEGIN IMMEDIATE` to serialize writers, reloads committed state while
holding that write reservation, applies the same in-memory policy, and commits
the complete batch only after validation succeeds. Database primary and unique
keys independently enforce the one-to-one asset/identity mapping.

SQLite write-lock acquisition uses a configurable finite timeout. A lock or
database failure becomes `PromotionRepositoryError`; callers may retry the
whole idempotent batch. The adapter enables WAL mode for concurrent readers,
but it intentionally does not distribute writes across network filesystems or
replace a client/server database where that deployment model is required.

## Versioned file state

Lifecycle and promotion records can be stored together in a schema-versioned
JSON document. The file adapter validates untrusted JSON with Pydantic, rejects
unknown schema versions, requires timezone-aware dates, checks consecutive
lifecycle generations and promotion-to-lifecycle links, and refuses updates
that discard prior generations, events, inactive keys, or promotions.

JSON state writes use a temporary file in the destination directory, flush and
synchronize
its contents, then atomically replace the destination. An expected revision
detects stale callers, while an identical replay leaves the revision unchanged.
This is safe against partial file writes. It is optimistic concurrency, not a
replacement for transactional multi-process locking. Use the SQLite promotion
repository when concurrent writers are required.

This separation prevents protocol-reported inventory from being mistaken for
operator-confirmed plant structure while preserving all evidence needed for a
later decision.
