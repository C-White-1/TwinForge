# Alarm and Trip Candidates

TwinForge derives an evidence-bound candidate set from controller and program
tags. It does not claim that naming conventions alone constitute a validated
alarm philosophy or shutdown cause-and-effect design.

## Inclusion rule

A tag is included only when its name or description explicitly contains one
of these lexical tokens:

- alarm, alarms, or `Alm`; or
- trip or trips.

Token matching handles separators and camel-case names. A tag may retain both
classifications when both meanings are explicit. The report records whether
each classification came from the name, description, or both.

Names such as `PT102_HH`, `Faulted`, `ESD`, or `Permissive` are not classified
without additional explicit alarm/trip evidence. They may be operationally
important, but TwinForge does not encode site-specific naming assumptions as
facts.

## Dependency evidence

Candidates are joined to the tag dependency graph to retain:

- program and controller scope;
- observed reader locations;
- observed writer locations; and
- aliases that target the candidate.

Missing reader or writer evidence means no supported reference was observed;
it does not prove that the tag is unused. Unsupported routine bodies and
unresolved operands remain subject to the dependency graph's documented
coverage boundary.

## Review boundary

The output is intentionally named an alarm/trip *candidate* report. A verified
alarm and trip list still requires engineering review of priority, setpoint,
units, delay, latching, acknowledgement, suppression, voting, shutdown action,
and operating-state applicability. None of those properties are invented when
the L5X evidence does not establish them.

## Attributable review overlay

The optional `--alarm-review` input applies engineer-reviewed fields without
changing the parsed controller, dependency graph, classification evidence, or
unreviewed candidates. The JSON document must use schema version
`twinforge.alarm-review.v1` and provide:

- the exact parsed controller name;
- reviewer, timezone-qualified review time, authority, and source references;
- unique, exact candidate `tag_key` values; and
- at least one non-empty review assertion for each listed candidate.

Unknown candidate keys, controller mismatches, duplicate rows, naive
timestamps, blank assertions, unknown properties, and unsupported schema
versions fail before the report directory is written. A partial review is
allowed and is identified by the exact applied tag keys in report provenance.

The overlay may assert priority, setpoint, engineering unit, delay, latching,
acknowledgement, suppression, shutdown action, and applicability. It cannot
change the derived alarm/trip classification or mark a cause-and-effect
relationship as verified. Those relationships need a separate,
location-specific engineering review.

## Report formats

The `twinforge report` bundle writes the candidate evidence as Markdown, CSV,
and deterministic JSON. The review columns include priority, setpoint, units,
delay, latching, acknowledgement, suppression, shutdown action, and
applicability. Empty CSV values, JSON `null` values, and Markdown em dashes all
mean that the source evidence did not establish the property.

Reviewed Markdown, CSV, and JSON outputs carry the reviewer, review time,
authority reference, and source reference. A copyable input document is
provided at `examples/reporting/alarm-review.example.json`.

The installed package also carries the machine-readable Draft 2020-12 schema
`twinforge.schemas/alarm-review.v1.schema.json`. Editors, CI jobs, and MCP
tools may validate review documents against it before submitting them to
TwinForge. Runtime validation remains authoritative because it also checks
controller identity and exact candidate keys against the parsed L5X evidence.

Cause-and-effect CSV, Markdown, and JSON rows carry an opaque deterministic
`relationship_key`. It is derived from the effect write, cause operand, source
location, instructions, and resolution status. Review tooling should use this
key rather than tag names: the same tags may participate in more than one
relationship or occur at multiple logic locations.

The optional `--cause-effect-review` document uses schema version
`twinforge.cause-effect-review.v1` and exact relationship keys from a previous
report. Each assertion records a `verified` or `rejected` disposition and may
add polarity, voting, delay, operating modes, and shutdown action. TwinForge
rejects unknown keys and will not verify an unresolved operand. Partial review
is allowed, remains visibly attributable, and leaves every omitted relationship
as `unreviewed`. A template is provided at
`examples/reporting/cause-effect-review.example.json`.

Its packaged Draft 2020-12 schema is
`twinforge.schemas/cause-effect-review.v1.schema.json`. Schema validation can
check document shape independently; runtime application remains authoritative
for controller matching, known relationship keys, and the rule that unresolved
relationships cannot be verified.

Every report bundle also includes `engineering_review_coverage.md` and
`engineering_review_coverage.json`. These summarize reviewed and complete
alarm candidates plus verified, rejected, unreviewed, and unresolved
relationships. Coverage is deliberately not labelled approval: completion and
safety acceptance remain engineering governance decisions.
