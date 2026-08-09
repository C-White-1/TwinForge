# Discovery Drift

TwinForge compares two normalized discovery states across four independent
evidence domains:

- hardware: direct CIP identities and bounded routed chassis slots;
- firmware: direct and routed CIP major/minor revisions;
- configuration: structural controller software inventory; and
- network: evidence-backed topology relationship candidates.

Each normalized record retains a stable domain key, inspectable attributes, and
references to the underlying evidence. Drift findings are classified as added,
removed, or changed and retain both the before and after records.

## Capture completeness

Every `DiscoveryDriftState` explicitly declares its complete domains. A domain
is compared only when both baseline and current states declare it complete.
Domains not complete on both sides are returned in `skipped_domains` and cannot
produce findings.

This prevents a capture that omitted software inventory, SNMP, or routed slots
from falsely reporting configuration, network, or hardware removal. A removal
is reported only when both captures explicitly claim complete coverage for that
domain and the normalized record is absent from the current state.

Declaring completeness requires the relevant evidence source. Hardware and
firmware require direct identity or routed evidence; configuration requires at
least one attributable software-inventory observation; and network completeness
requires a topology-correlation result. An intentionally complete empty direct
identity capture is permitted and can therefore report removals.

## Interpretation

Drift is an evidence difference, not an automatic maintenance conclusion. For
example, a changed product code may indicate replacement, while a disappeared
LLDP relationship may reflect a genuine cable change, capture scope, or device
availability. Reports retain provenance so an operator can review the cause
before changing the core model.

## Sanitized reports

`sanitize_discovery_drift` produces a public-safe intermediate report for JSON
or Markdown export. Findings receive deterministic sequential references such
as `DRIFT-0001`; raw record keys are not hashed or emitted because small address
spaces could make unsalted hashes reversible by enumeration.

The sanitizer removes target and route keys, tag and program names, serial
numbers, product names, raw evidence identifiers, and free-form evidence
descriptions. Domain-specific allowlists retain only reviewable attributes such
as numeric product classification, firmware revision, structural data type or
language, and non-identifying topology properties. Provenance is reduced to
protocol names and capture timestamps.

Confidence is retained from network topology evidence. Other findings are
reported as `protocol_reported`, `corroborated` when multiple evidence protocols
support the record, or `indirect` when no protocol evidence is present. The
sanitized report is suitable for sharing, but the full internal drift result
must remain available for authorized investigation.
