# pycomm3 Software Inventory Lab Validation

## Purpose

This procedure validates TwinForge's experimental Logix Symbol page transport
against an explicitly authorized, non-production controller. It does not
authorize scanning, public-address access, runtime tag-value reads, writes, or
controller changes.

Successful offline packet tests are necessary but do not prove that a live
controller accepts the selected service, attributes, and route. Until this
procedure succeeds, the adapter remains experimental.

## Preconditions

- The controller and TwinForge host are owned by, or explicitly authorized by,
  the laboratory operator.
- The directly contacted gateway uses an RFC 1918, loopback, or IPv4
  link-local address.
- The exact CIP route has been independently confirmed. Do not discover a route
  by trying arbitrary ports, links, or chassis slots.
- The controller is non-production or an approved maintenance window is active.
- The controller project is backed up and no TwinForge runtime-value or write
  capability is enabled.
- The engagement, authorization, operator, and laboratory evidence references
  have been recorded outside the repository.

## Stage 1: dry-run review

Generate a plan without opening a network connection:

```powershell
uv run twinforge discover software 192.168.1.10 `
  --route-segment 1/0 `
  --engagement "Authorized Logix laboratory" `
  --authorization-reference LAB-CHANGE-001 `
  --capability programs `
  --maximum-requests 2 `
  --output artifacts/software-plan.json
```

Replace the example address, route, and references with approved values. Review
the generated JSON and confirm:

- `dry_run` is `true`;
- `runtime_values_permitted` is `false`;
- the target and every route segment are exact;
- only `programs` is initially requested; and
- the request budget is no greater than two.

## Stage 2: minimal live capture

After reviewing the dry run, repeat the command with the explicit execution
confirmation fields:

```powershell
uv run twinforge discover software 192.168.1.10 `
  --route-segment 1/0 `
  --engagement "Authorized Logix laboratory" `
  --authorization-reference LAB-CHANGE-001 `
  --capability programs `
  --maximum-requests 2 `
  --execute-experimental `
  --confirmed-by "laboratory operator" `
  --confirmed-at "2026-08-09T10:00:00+10:00" `
  --laboratory-evidence-reference LAB-PACKET-001 `
  --output artifacts/software-observation.json
```

Use the real confirmation time. Do not copy the example timestamp.

Stop and retain the diagnostic if the controller rejects the service, returns
malformed evidence, repeats a cursor, or exhausts the request budget. Do not
increase the budget merely to suppress a failure.

## Stage 3: controlled capability expansion

Only after the programs-only capture succeeds, repeat the dry-run review and
live capture while adding one capability at a time in this order:

1. `tasks`
2. `routines`
3. `tag_definitions`

Program-scope enumeration can require more than one page. Set a new explicit
request budget from the reviewed project size and retain each failed or
successful run as separate evidence. TwinForge must never return runtime tag
values during these captures.

## Acceptance criteria

The live adapter can be marked validated only when all of the following are
demonstrated on a supported controller:

- every request occurred within the declared budget;
- the exact target and route in the observation match the reviewed plan;
- the engagement, authorization, confirmation, adapter version, and laboratory
  evidence reference are present;
- program, task, routine, and tag-definition names agree with an independently
  reviewed offline L5X export or controller project;
- partial-transfer pagination terminates without a repeated cursor;
- raw object evidence is retained for every page;
- no runtime values, writes, downloads, or controller changes occurred; and
- a second capture of an unchanged project produces the same structural items.

Record the controller family, catalog number, firmware revision, Studio 5000
project version, installed `pycomm3` version, and TwinForge commit separately
with the laboratory evidence.

## Sanitization and repository policy

Do not commit unsanitized live observations by default. They can contain IP
addresses, controller and program names, tag definitions, serial numbers in
associated evidence, operator identity, and raw packet bytes.

A repository fixture must use a separately reviewed sanitized copy. Record
what was replaced, preserve structural relationships, and ensure the fixture
cannot be mistaken for raw laboratory evidence.

## Failure reporting

For a failed validation, retain:

- the dry-run plan;
- the TwinForge diagnostic and exit code;
- controller family and firmware;
- the requested capability and request budget;
- whether any page completed successfully; and
- a sanitized packet trace when laboratory policy permits it.

Do not classify an unsupported service, controller revision, or route as an
empty software inventory.
