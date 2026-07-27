# Parameter and setpoint reports

TwinForge can combine device-parameter access observed in controller software
with vendor-neutral catalogue semantics. The result is available as concise
Markdown and detailed CSV.

For a related L5X corpus:

```powershell
uv run python examples\export_parameter_report.py `
  reference\L5X\LogixLibraries\Powerflex525 `
  reports\Dev_PF525_Program\parameter_setpoint_report.md `
  reports\Dev_PF525_Program\parameter_setpoint_report.csv
```

Use `--device NAME` when a corpus assembles more than one physical device.
TwinForge rejects ambiguous selection rather than silently reporting the
wrong device.

## Value semantics

The report keeps three different facts separate:

- **Default** is catalogue information from the cited device documentation.
- **Configured value** is populated only when an offline source provides
  evidence of the application-requested value.
- **Runtime value** requires online discovery or captured runtime data.

An empty configured or runtime value therefore means “not available from the
supplied evidence.” It does not mean zero, the documented default, or an
unknown live value.

The current PowerFlex report provides complete semantics for all 163
parameters observed by the reference AOI. It recovers configured values when
an AOI `Cfg_*` member is backed by a unique decorated instance value and an
exact label or setpoint-alias relationship. Further recovery from internal
write logic follows parsed `WriteInstance` and `WriteParam` branches. When a
writable parameter still has no exported value, the report distinguishes an
internal unexported setpoint from an automatic literal-write behavior rather
than presenting the literal as saved configuration.

## Output fields

The CSV includes purpose, units, bounds, default, resolution, observed access,
read-only status, stop-required constraints, source reference, and evidence.
It also reserves separate value and provenance fields for configured and
runtime observations. `ConfigurationNote` explains writable parameters whose
configured value cannot be promoted safely. `ConfiguredValueLabel` gives the
documented meaning of an enumerated raw value while leaving
`ConfiguredValue` unchanged. `ConfiguredValueAssessment` checks enumerated
options and purely numeric bounds. Symbolic or drive-dependent constraints
remain explicitly not automatically verifiable.

Structured parameter advisories retain their QA code, severity, summary, and
reference. They identify manual-review findings without modifying the source
AOI or treating an advisory as a confirmed runtime defect. The Markdown
report collects high- and medium-severity findings in a review-priority
section with configured-value context.
