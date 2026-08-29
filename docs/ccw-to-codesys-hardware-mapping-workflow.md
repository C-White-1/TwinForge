# CCW-to-CODESYS hardware migration workflow

This walks through sizing physical I/O for a Micro800 (CCW) project, picking
replacement hardware, and recording an attributable, auditable binding of
every physical point onto that hardware — using the real
`reference/ccw-tests/M10_Conveyor.json` fixture end to end. It complements
[the CCW project interchange architecture doc](architecture/ccw-project-interchange.md),
which explains *why* each boundary exists; this doc is the practical
walkthrough of *how* to use it.

No step here guesses a physical address. Where TwinForge can't be certain,
it says so explicitly (an `unresolved` binding, an `unmapped` point, a
`compatibility_confirmed: false` flag) rather than inventing an answer.

## 1. Validate and inspect the source project

```powershell
uv run twinforge ccw-project validate .\M10_Conveyor.json
uv run twinforge ccw-project inspect .\M10_Conveyor.json
```

Confirms the artifact matches the vendored `ccw-project-v1` schema and shows
the basic inventory (programs, rungs, variables, diagnostics) before any
semantic interpretation happens.

## 2. Size the physical I/O, independent of any target

```powershell
uv run twinforge ccw-project io-summary .\M10_Conveyor.json
```

For M10 Conveyor this reports 48 physical points on the `2080-LC50-48QWB-SIM`
base unit — 28 `Input/Digital`, 20 `Output/Digital` — with an
`assigned`/`spare` status per point and an `assigned_unaliased_point_count`
flag for points CCW auto-buffered but that carry no engineer-given alias
(a real signal that they're likely spare capacity, not active logic — 42 of
the 48 in this fixture, since only 6 have meaningful names: `Stop_PB`,
`Start_PB`, `1PE`, `2PE`, `Size_Fault`, `Motor_01`).

This command only reads the neutral CCW lowering. It has no opinion about
CODESYS, or any other target — the same sizing report would apply whichever
platform you migrate to.

## 3. Pick replacement hardware

Not a TwinForge command — an engineering decision, informed by the sizing
report above (I/O count and type) plus any other requirements (analog,
high-speed counting, EtherNet/IP scanning for networked devices). For this
fixture: no analog, no HSC, no networked devices, so a low-cost digital-only
CODESYS controller fits — AutomationDirect's ProductivityCODESYS
(`P2CDS-622` CPU + `P2-16ND3-1` 16-ch DI + `P2-16TD1P` 16-ch DO modules),
chosen here specifically because it's price-comparable to the now-discontinued
Micro850 this project targeted.

## 4. Define the I/O card library

A versioned, user-authored catalog of the target hardware's electrical
specs — TwinForge validates the format but never supplies the parts data
itself. See `examples/reporting/io-card-library.example.json`:

```json
{
  "schema_version": "twinforge.io-card-library.v1",
  "cards": [
    {
      "part_number": "P2-16ND3-1",
      "vendor": "AutomationDirect",
      "direction": "Input",
      "signal_type": "Digital",
      "channel_count": 16,
      "voltage": "12-24VDC"
    },
    {
      "part_number": "P2-16TD1P",
      "vendor": "AutomationDirect",
      "direction": "Output",
      "signal_type": "Digital",
      "channel_count": 16,
      "voltage": "12-24VDC"
    }
  ]
}
```

Export and inspect the schema behind it at any time:

```powershell
uv run twinforge review schema io-mapping --output .\io-mapping-review.schema.json
```

(The card library's own schema is packaged at
`twinforge.schemas:io-card-library.v1.schema.json`.)

This library is reusable across every project you migrate onto the same
hardware family — define it once, reference it from many mapping reviews.

## 5. Author the mapping review

One JSON document, one engineer's attestation, binding known physical
addresses onto specific card instance/channel combinations. See
`examples/reporting/io-mapping-review.example.json` — mapping M10's 6
functionally-used points onto one `P2-16ND3-1` (`"DI-1"`) and one
`P2-16TD1P` (`"DO-1"`):

```json
{
  "schema_version": "twinforge.io-mapping-review.v1",
  "controller_name": "M10 Conveyor",
  "reviewed_by": "Control systems engineer",
  "reviewed_at": "2026-08-29T10:00:00+10:00",
  "authority_reference": "ProductivityCODESYS hardware selection, 2026-08-29",
  "source_reference": "reference/ccw-tests/M10_Conveyor.json",
  "items": [
    { "physical_address": "_IO_EM_DI_00", "card_part_number": "P2-16ND3-1", "card_instance": "DI-1", "channel": 0 },
    { "physical_address": "_IO_EM_DI_01", "card_part_number": "P2-16ND3-1", "card_instance": "DI-1", "channel": 1 },
    { "physical_address": "_IO_EM_DI_02", "card_part_number": "P2-16ND3-1", "card_instance": "DI-1", "channel": 2 },
    { "physical_address": "_IO_EM_DI_03", "card_part_number": "P2-16ND3-1", "card_instance": "DI-1", "channel": 3 },
    { "physical_address": "_IO_EM_DO_00", "card_part_number": "P2-16TD1P", "card_instance": "DO-1", "channel": 0 },
    { "physical_address": "_IO_EM_DO_01", "card_part_number": "P2-16TD1P", "card_instance": "DO-1", "channel": 1 }
  ]
}
```

`reviewed_by`/`reviewed_at`/`authority_reference`/`source_reference` are
mandatory attribution — this is a human sign-off, not a generated artifact.
You don't have to map every point in one pass; anything left out is reported
as `unmapped`, not silently accepted as "done."

## 6. Validate it against the real project and card library

```powershell
uv run twinforge review validate io-mapping .\io-mapping-review.json `
  --source .\M10_Conveyor.json `
  --io-card-library .\io-card-library.json `
  --output .\io-mapping.receipt.json
```

This is where every guardrail runs: unknown physical addresses, unknown
part numbers, channels outside a card's `channel_count`, direction/signal-type
mismatches, and duplicate channel assignments are all rejected here with a
specific, actionable error — not a generic failure. `--source` and
`--io-card-library` are optional together (you can validate a review's
internal shape alone) but required as a pair; supplying only one is rejected
rather than silently skipping reconciliation.

A successful run writes a JSON receipt recording the exact SHA-256 of both
the review file and the source project, plus the resolved item count.

## 7. Verify the receipt later

```powershell
uv run twinforge review verify-receipt io-mapping .\io-mapping.receipt.json `
  --review .\io-mapping-review.json `
  --source .\M10_Conveyor.json `
  --io-card-library .\io-card-library.json
```

This re-derives the receipt from the exact same inputs and byte-compares —
genuinely hash-bound, not just "the file still exists." Edit one byte of
either the review or the source project and this fails, naming exactly which
fields drifted (`review_sha256`, `source_sha256`, etc.). Use this in CI, or
before trusting a receipt someone else produced, to confirm nothing changed
underneath it.

## Where this stops today

The validated mapping produces an `IOMappingReport` — every physical point
resolved to a card+channel, or explicitly `unmapped` — but that report is
not yet consumed anywhere else. `ccw-project export`'s generated PLCopen XML
still carries no physical `AT` address bindings, and its coverage report's
`physical_io_binding_status` field still reports the placeholder
`requires_codesys_device_mapping` regardless of whether a mapping review
exists. Wiring a validated `IOMappingReport` into that export path is the
next step, tracked in `ROADMAP.md` under "CCW project interchange and
CODESYS conversion."
