# CCW project interchange boundary

TwinForge consumes Connected Components Workbench evidence through a versioned
JSON contract. It does not decode `.ccwarc` archives and does not import Python
code from the separate `rockwell-file-research` repository.

## Contract provenance

The packaged `ccw-project-v1.schema.json` is an exact snapshot of the Draft
2020-12 schema generated and maintained by `rockwell-file-research` for its
`ccw-project-v1` export. Its stable identifier is
`urn:rockwell-file-research:ccw-project:v1`.

The initial vendored snapshot has SHA-256
`a339b755aea53f119de6bd621979dfee91d7b6355dddd3aa0f4472319454c37a`.
This hash is the same in both repositories at the time of integration.

Update the snapshot only when the producing repository intentionally publishes
a compatible or newly versioned contract. TwinForge must add explicit support
for a new `schema_version`; it must not silently interpret one version as
another.

## Responsibility boundary

```text
.ccwarc archive
    -> rockwell-file-research capture and parsing
    -> ccw-project-v1.json
    -> TwinForge validation and lossless interchange capture
    -> TwinForge vendor-neutral semantic lowering
    -> future target-specific conversion
```

The input adapter retains the complete validated document, including source provenance,
SHA-256 evidence, parser diagnostics, unresolved operands, sensitive-entry
names, and unknown-entry names.

The neutral lowerer imports variables, aliases, physical-I/O evidence,
programs, rungs, and recursive series/parallel topology. It assigns neutral
semantics to `XIC`, `XIO`, `OTE`, `OTS`, `OTU`, and CCW's `OTR` reset-coil
mnemonic. Every other mnemonic remains
an explicit unsupported instruction carrying its original mnemonic, operand,
annotations, and position, accompanied by a diagnostic. The complete source
record also remains attached as a source extension.

For supported ladder networks, common serial conditions remain before and
after a parallel section in the PLCopen connection graph. TwinForge does not
distribute those contacts into duplicated Boolean paths merely to obtain an
equivalent expression; this keeps imported CODESYS ladder structure comparable
to the CCW source. TwinForge currently only converts a condition section that
is a single flat parallel group (optionally preceded and followed by flat
serial conditions). A rung with two or more parallel groups in series, a
nested parallel, or a parallel branch with no captured elements is preserved
as attributable evidence rather than converted, so that TwinForge never
silently duplicates a shared condition across paths to force a conversion.

This boundary does not yet claim that CCW ladder logic can be converted to
every PLCopen XML target or CODESYS construct. The initial CODESYS adapter
creates `PLC_PRG`, represents source programs as actions, and schedules the
program from a periodic `MainTask`. It emits only rungs whose semantics and
topology are supported; other rungs remain attributable non-executable
evidence in the XML and coverage report.

The schema deliberately rejects undeclared JSON members. Evidence that the
producer cannot interpret remains represented through its documented
diagnostic and unknown-entry fields rather than being discarded or guessed by
TwinForge.

## Command line

Validate or inspect an artifact:

```powershell
uv run twinforge ccw-project validate .\project.json
uv run twinforge ccw-project inspect .\project.json
uv run twinforge ccw-project inspect .\project.json --format json
```

Inspect the neutral lowering without producing a target artifact:

```powershell
uv run twinforge ccw-project lower .\project.json
uv run twinforge ccw-project lower .\project.json --format json
```

Size the physical I/O a project requires, before any conversion target is
chosen. This reads only `physical_source`, `physical_destination`, `aliases`,
and `data_type` from the neutral lowering, so it applies to any future
TwinForge target adapter, not just CODESYS; it depends on the CCW lowerer's
metadata convention, so it does not yet generalize to a non-CCW source.
Direction and signal type are reported using the same `IODirection` /
`IOSignalType` vocabulary as the L5X `io_list` report
(`src/twinforge/analysis/io_list.py`), and each point's `assigned`/`spare`
status matches that report's meaning: a tag exists that references the
physical address. CCW's own buffer-program convention makes `assigned` a
weaker signal of real use than in L5X, since CCW commonly auto-generates a
buffer variable for every embedded point whether or not the logic uses it;
`assigned_unaliased_point_count` distinguishes a bound-but-unnamed point from
one an engineer actually named. Unlike L5X, CCW never declares a channel's
nominal or configured count, so there is no `unavailable_by_configuration`
status, and a binding with no matching `physical_io`-classified variable is
reported separately as an unresolved binding rather than invented as a point:

```powershell
uv run twinforge ccw-project io-summary .\project.json
uv run twinforge ccw-project io-summary .\project.json --format json
```

Export the supported subset for CODESYS and always write its conversion
coverage alongside it:

```powershell
uv run twinforge ccw-project export .\project.json `
  --target codesys `
  --output .\project-codesys.xml `
  --coverage .\project-codesys.coverage.json
```

The default cyclic interval is 20 ms. Use `--task-rate-ms` when the target
application requires a different explicitly reviewed interval.

### CODESYS global variables and physical I/O

The initial adapter emits one `ControllerTags` Global Variable List containing
both CCW user variables and captured physical-I/O symbols. This is necessary
because CCW buffer programs copy physical inputs into user variables and user
outputs into physical outputs. User-variable comments contain only the alias
text so CODESYS ladder diagrams remain readable. Physical source, destination,
scope, and classification remain machine-readable in TwinForge PLCopen
`addData` rather than being rendered above every contact and coil.

TwinForge does not convert names such as `_IO_EM_DI_00` into guessed CODESYS
addresses. The coverage report counts user and physical variables separately,
counts every other CCW classification (`system`, `register`, `compiler`) in
`other_classification_variable_count` so the counts reconcile against
`global_variable_count`, and reports `requires_codesys_device_mapping` until a
device-specific binding has been supplied and validated.

### I/O card library and mapping-review fixture

Resolving `requires_codesys_device_mapping` requires knowing two things
TwinForge cannot derive from the CCW project alone: what target hardware I/O
cards exist, and which physical point an engineer intends for each channel.
TwinForge never guesses either. Instead it reuses the same attributable,
hash-receipted engineering-review pattern already used for alarm and
cause-and-effect review, as a third `io-mapping` kind of the `review` command.

An **I/O card library** is a user-authored, versioned catalog of target
hardware module specs (part number, vendor, direction, signal type, channel
count) — `src/twinforge/knowledge/io_card_catalog.py`, validated against
`io-card-library.v1.schema.json`. TwinForge ships no built-in cards; see
`examples/reporting/io-card-library.example.json` for a starting example.

An **I/O mapping review** binds known CCW physical points (from
`ccw-project io-summary`'s evidence) onto specific card instance/channel
combinations — `src/twinforge/analysis/io_mapping_review.py`, validated
against `io-mapping-review.v1.schema.json`. Applying one rejects: an unknown
physical address, an unknown card part number, a channel outside the card's
`channel_count`, a direction/signal-type mismatch between the CCW point and
the resolved card, and two points assigned the same card channel. A CCW
point whose own direction/signal type is unresolved may still be mapped, but
its resolution is marked `compatibility_confirmed: false` — no evidence
contradicted the binding, but none confirmed it either. Every known point
not covered by the review is reported as `unmapped`, never silently dropped.

```powershell
uv run twinforge review schema io-mapping --output .\io-mapping-review.schema.json
uv run twinforge review validate io-mapping .\io-mapping-review.json `
  --source .\project.json `
  --io-card-library .\io-card-library.json `
  --output .\io-mapping.receipt.json
uv run twinforge review verify-receipt io-mapping .\io-mapping.receipt.json `
  --review .\io-mapping-review.json `
  --source .\project.json `
  --io-card-library .\io-card-library.json
```

`--source` and `--io-card-library` are optional together (schema-only
validation) but required as a pair — supplying one without the other is
rejected rather than silently skipping reconciliation.

**Scope boundary:** this produces a validated, hash-bound `IOMappingReport`
only. It is not yet wired into `ccw-project export`'s generated PLCopen XML
(no physical `AT` address emission) and does not yet change the coverage
report's `physical_io_binding_status` placeholder — that is a follow-up once
this mechanism is in routine use.

## Reviewed empty-rung evidence

Manual inspection in Connected Components Workbench on 28 August 2026
confirmed that `M10 Conveyor` program `Buffer_Inputs`, rung 29 is an empty
source rung. TwinForge therefore classifies an explicitly empty network as
`empty`, emits an intentional `NOP`, and reports it with its own coverage
status, distinct from `converted` and from `preserved` (which covers every
rung TwinForge did not convert, whether because of an unsupported
instruction, uncaptured topology, or a condition structure it will not
convert without duplicating a shared condition; each `preserved` entry
carries its own `reason` text). No executable logic is inferred.

Export the exact schema snapshot used by the installed TwinForge version:

```powershell
uv run twinforge ccw-project schema --output .\ccw-project-v1.schema.json
```
