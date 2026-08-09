# Relationship Evidence Classes

TwinForge emits an explicit `evidence_class` wherever a discovery or assembly
result represents a relationship. This classification states how the link is
known independently of its domain meaning or qualitative confidence.

- `protocol_reported`: a protocol directly reported the relationship, such as
  an LLDP remote-systems entry.
- `indirect_inference`: evidence supports reachability or association but not a
  physical link, such as a bridge forwarding entry.
- `configured_intent`: offline configuration expresses intended communication,
  such as an explicitly bound Logix `MESSAGE` tag.
- `operator_accepted`: an attributable review accepted a reported candidate
  and mapped its endpoints or assets.
- `cross_layer_corroborated`: independent software, configuration, routed
  observation, and accepted mapping layers join without merging their objects.

Confidence and evidence class answer different questions. A reported LLDP link
may be `corroborated` by forwarding evidence while remaining
`protocol_reported`; the forwarding-only relationship remains
`indirect_inference`. Operator acceptance does not rewrite the source candidate
or imply that configured intent was observed at runtime.

The classification appears in topology candidate JSON, accepted topology and
chassis mapping JSON, configured controller communication graphs, cross-layer
device correlations, network drift records, and sanitized drift reports. This
keeps inference visible through every downstream serialization boundary.
