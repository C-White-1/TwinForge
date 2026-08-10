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
