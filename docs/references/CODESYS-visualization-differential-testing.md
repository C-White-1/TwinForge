# CODESYS visualization differential testing

CODESYS native `.export` files are profile-dependent object archives rather
than PLCopen XML. Many visual-element properties are stored under numeric
member identifiers. TwinForge must establish their meaning from controlled
evidence instead of assuming that an identifier is stable or universal.

## Experiment protocol

1. Keep an unchanged baseline project and export its visualization.
2. Change exactly one editor property on exactly one control.
3. Export the modified visualization under a new numbered filename.
4. Do not edit or reformat either export.
5. Generate a differential report:

```powershell
uv run python examples/diff_codesys_visualizations.py `
  reference/PLCopenXML/codesys-native/12_powerflex_visualization.export `
  reference/PLCopenXML/codesys-native/13_button_x.export `
  reports/Dev_PF525_Program/codesys_diff_13_button_x.md
```

The report separates known properties, opaque numeric properties, bindings,
actions, element additions or removals, and Visualization Manager changes.
Both source archives remain the authority.

## Recommended first series

Use `12_powerflex_visualization.export` as the baseline and alter the Run
Forward button unless the row specifies another object.

| Export | Single deliberate change |
| --- | --- |
| `13_button_x.export` | Move X position from 120 to 130 |
| `14_button_y.export` | Move Y position from 47 to 57 |
| `15_button_width.export` | Change width from 150 to 160 |
| `16_button_height.export` | Change height from 30 to 40 |
| `17_button_text.export` | Change text from Run Forward to Start Forward |
| `18_button_binding.export` | Bind Toggle to a different Boolean variable |
| `19_button_action.export` | Change or remove only the Toggle action |
| `20_speed_format.export` | Change only the speed field display format |
| `21_speed_limit.export` | Change only the speed field maximum from 60 to 65 |
| `22_manager_style.export` | Change only the Visualization Manager style |
| `23_stop_button_x.export` | Move the Stop button X position from 304 to 314 |
| `24_stop_button_y.export` | Move the Stop button Y position from 47 to 57 |

Export from the same CODESYS profile first. Cross-profile repetition is a
separate experiment because identical editor properties may use different
archive types, member IDs, defaults, or serialization behavior.

## Acceptance rule

A single matching change is evidence, not proof. A numeric-property mapping
becomes a candidate after isolated repetition on more than one compatible
control. It should remain marked profile-specific until repeated under another
CODESYS profile. Any unrelated archive churn is retained and reported rather
than discarded.

Verified mappings are registered by exact profile name in
[`codesys_native_profiles.py`](../../src/twinforge/parsers/codesys_native_profiles.py).
There is deliberately no closest-version or prefix matching. An unknown
profile retains its complete source XML, raw element XML, and numeric members,
but receives no friendly property names until evidence is collected for that
exact serialization profile.

## Recorded results

Experiment 13 changed the Run Forward button X position from 120 to 130. The
known X property `1649127785` followed the editor value directly. Property
`550940142` changed from 195 to 205; with width fixed at 150, both values equal
X plus half the width. It is recorded as a candidate derived horizontal centre
in
[`codesys_visualization_property_evidence.md`](../../reports/Dev_PF525_Program/codesys_visualization_property_evidence.md),
pending the width-only experiment.

Experiment 14 was exported from experiment 13 rather than from the original
baseline. Comparing exports 13 and 14 cleanly isolates the Y change:
`357335551` changed from 47 to 57, while `1473355128` changed from 62 to 72.
With height fixed at 30, the latter equals Y plus half the height and is
recorded as a candidate derived vertical centre.

Experiment 15 changed width from 150 to 160 with X fixed at 130. The direct
width property `2422045748` followed the editor value, while `550940142`
changed from 205 to 210. This is exactly half the width delta and independently
confirms the X-plus-half-width calculation for this control. It remains a
profile-specific candidate until repeated on another rectangular control.

Experiment 16 changed height from 30 to 40 with Y fixed at 57. The direct
height property `2134141914` followed the editor value, while `1473355128`
changed from 72 to 77. This is exactly half the height delta and independently
confirms the Y-plus-half-height calculation for this control.

Experiment 17 changed Run Forward to Start Forward. Property `390574330`
followed the editor text directly. Opaque property `823443203` also changed
from 712 to 701, but values observed on other text-bearing controls do not
support a specific interpretation. It remains preserved as an unresolved
text-dependent derived value.

Experiment 18 changed only the Toggle binding from
`PLC_PRG.xInp_PRunFwd` to `PLC_PRG.xInp_PStop`. No numeric member changed.
This confirms that the binding is self-describing evidence within the
configured Toggle action and can be decoded without an opaque-property map.

Experiment 19 removed the Toggle action. Its `PLC_PRG.xInp_PStop` binding
disappeared with it, while the numeric visual-property map remained unchanged.
This confirms the action/operand ownership boundary.

Experiment 20 changed only `InputBox.Format` from `%.2f` to `%.1f`. No
binding or numeric visual property changed. The setting is self-describing
action data and is emitted as an isolated action-property transition by the
differential report.

Experiment 21 changed only `InputBox.InputBoxMax` from 60 to 65. The binding,
format, minimum, and numeric visual-property map remained unchanged. The input
limit is therefore another directly decodable action property.

Experiment 22 changed the Visualization Manager style from Basic style to
CODESYS Demo Style. No visual element changed. This confirms that the style is
self-describing manager data and is not baked into each control's serialized
property map.

Experiment 23 repeated the X-position test on the Stop button. Property
`1649127785` changed from 304 to 314 and `550940142` changed from 379 to 389,
with width fixed at 150. This confirms `550940142` as `center_x` across two
controls for the tested CODESYS SP22 profile.

Experiment 24 repeated the Y-position test on the Stop button. Property
`357335551` changed from 47 to 57 and `1473355128` changed from 62 to 72, with
height fixed at 30. This confirms `1473355128` as `center_y` across two
controls for the tested CODESYS SP22 profile.

## Remaining opaque-property register

Experiment 24 contains 31 unmapped property IDs across 143 element-property
occurrences. The generated
[`codesys_visualization_opaque_properties.md`](../../reports/Dev_PF525_Program/codesys_visualization_opaque_properties.md)
ranks them by occurrence and records control types and preserved sample
values. It deliberately assigns no friendly names.

The next useful controlled series should vary common editor properties on both
buttons so each candidate can be repeated across compatible controls:

| Export | Single deliberate change |
| --- | --- |
| `34_run_button_horizontal_alignment.export` | Change Run button horizontal text alignment |
| `35_stop_button_horizontal_alignment.export` | Repeat the same alignment change on Stop |
| `36_run_button_font_style.export` | Change Run button font from Default to Title |
| `37_stop_button_font_style.export` | Repeat the same font-style change on Stop |
| `38_run_button_custom_font.export` | Establish an explicit custom-font baseline |
| `39_run_button_custom_font_size.export` | Change only the explicit custom-font size |

These experiments are recommendations, not inferred mappings. Each pair must
be inspected before any numeric property is promoted into the SP22 profile.

Experiment 34 changed the Start Forward button's horizontal text alignment
from centered to left. Property `2340015797` changed from `HCENTER` to `LEFT`;
no other element property, binding, action, or manager setting changed. The
property is therefore a profile-specific candidate for horizontal text
alignment, pending repetition on the Stop button in experiment 35.

Experiment 35 repeated the centered-to-left transition on the Stop button.
Property `2340015797` again changed from `HCENTER` to `LEFT`, with its binding
and Toggle action unchanged. This satisfies the local repetition rule, so the
property is promoted to `horizontal_alignment` for the exact SP22 Patch 2
profile.

Experiment 36 changed the Start Forward button font selection from `Default`
to `Title`. Structured property `3729828405` changed from `Font-Standard`,
Arial 12 to `Font-Title`, Arial Narrow 38. Correlated property `663104332`
changed the resolved `Element-Button-FontColor`. Both remain candidates until
the Stop button repeats the same style transition in experiment 37.

Experiment 37 repeated the `Default` to `Title` transition on the Stop button.
Structured property `3729828405` repeated exactly and is promoted to `font`
for the SP22 Patch 2 profile. Property `663104332` did not change on the Stop
button and therefore remains an unresolved, preserved color correlation.
