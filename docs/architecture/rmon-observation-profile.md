# RMON Observation Profile

TwinForge treats RMON statistics as an optional telemetry profile, separate
from baseline SNMP identity, inventory, interface, and topology capture.

## Decision

The `rmon-ethernet-statistics` profile is:

- disabled by default;
- bounded to the RFC 2819 `etherStatsTable` root
  (`1.3.6.1.2.1.16.1.1`);
- classified as `evidence_only`; and
- excluded from the baseline OID allowlist.

This decision follows [RFC 2819](https://www.rfc-editor.org/rfc/rfc2819), which
defines the Ethernet statistics group as optional and describes its values as
free-running counters for monitored Ethernet interfaces.

## Why it is separate

RMON statistics describe changing traffic conditions rather than stable asset
identity or physical connectivity. Meaningful interpretation requires capture
time, interface association, counter continuity, discontinuity handling, and
usually comparison between samples. Adding those counters to every discovery
snapshot would increase volume without strengthening the default asset model.

Some agents expose statistics only after a valid monitoring row exists.
TwinForge remains read-only and therefore never creates, activates, or modifies
RMON control rows. An empty result can mean unsupported RMON, an unconfigured
agent, or no monitored interfaces; it is not interpreted as zero traffic.

## Future lowering boundary

A future telemetry model may lower RMON counters after it defines:

- counter width, wrap, and reset semantics;
- collection-window and continuity evidence;
- explicit interface resolution;
- units and rate calculations; and
- retention policies appropriate for time-series observations.

Until then, an explicitly captured RMON profile remains raw evidence and does
not mutate assets, interfaces, network links, or accepted topology.
