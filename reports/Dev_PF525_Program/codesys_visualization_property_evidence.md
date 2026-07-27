# CODESYS visualization property evidence

This register records controlled native-export experiments. Candidate meanings
remain profile-specific and are not promoted into parser mappings from a
single observation.

## Profile

CODESYS V3.5 SP22 Patch 2

## Evidence register

| Property ID | Candidate meaning | Evidence | Status |
| --- | --- | --- | --- |
| 1649127785 | Element left/X position | Run Forward button moved from X 120 to 130; value changed from 120 to 130 | Known from baseline decoding and confirmed by experiment 13 |
| 550940142 | Derived horizontal centre (`center_x`) | Experiments 13 and 15 isolated X and width on the Run Forward button; experiment 23 repeated the X relationship on the Stop button | Confirmed profile mapping across two controls |
| 357335551 | Element top/Y position | Run Forward button moved from Y 47 to 57; value changed from 47 to 57 | Known from baseline decoding and confirmed by experiment 14 |
| 1473355128 | Derived vertical centre (`center_y`) | Experiments 14 and 16 isolated Y and height on the Run Forward button; experiment 24 repeated the Y relationship on the Stop button | Confirmed profile mapping across two controls |
| 390574330 | Display text | Run Forward changed to Start Forward and the property followed the editor text directly | Known from baseline decoding and confirmed by experiment 17 |
| 823443203 | Text-dependent derived value | Run Forward to Start Forward changed the value from 712 to 701; other controls carry unrelated values | Unresolved; preserve without assigning semantics |

## Experiment 13

- Baseline: `12_powerflex_visualization.export`
- Variant: `13_button_x.export`
- Intended change: Run Forward button X position from 120 to 130
- Changed element: `VISU_PowerFlex525_Test / GenElemInst_2`
- Unchanged evidence: type, width, height, text, binding, and Toggle action
- Differential report:
  [`codesys_diff_13_button_x.md`](codesys_diff_13_button_x.md)

The second changed property appears derived from geometry. It is therefore
expected serialization behavior rather than evidence that the experiment was
contaminated. A width-only experiment will distinguish a horizontal centre
from another X-derived value.

## Experiment 14

- Baseline: `13_button_x.export`
- Variant: `14_button_y.export`
- Intended change: Run Forward button Y position from 47 to 57
- Changed element: `VISU_PowerFlex525_Test / GenElemInst_2`
- Unchanged evidence: X, width, height, text, binding, and Toggle action
- Differential report:
  [`codesys_diff_14_button_y.md`](codesys_diff_14_button_y.md)

The variant retained experiment 13's X position, so the adjacent export was
used as the baseline. Property `1473355128` follows Y plus half the fixed
height and is therefore a candidate derived vertical centre.

## Experiment 15

- Baseline: `14_button_y.export`
- Variant: `15_button_width.export`
- Intended change: Run Forward button width from 150 to 160
- Changed element: `VISU_PowerFlex525_Test / GenElemInst_2`
- Direct property: `2422045748` changed from 150 to 160
- Derived property: `550940142` changed from 205 to 210
- Differential report:
  [`codesys_diff_15_button_width.md`](codesys_diff_15_button_width.md)

With X fixed at 130, the derived values satisfy `130 + 150 / 2 = 205` and
`130 + 160 / 2 = 210`. This independently supports the horizontal-centre
meaning. Repetition on another rectangular control is still required before
promoting it into the parser's known-property map.

## Experiment 16

- Baseline: `15_button_width.export`
- Variant: `16_button_height.export`
- Intended change: Run Forward button height from 30 to 40
- Changed element: `VISU_PowerFlex525_Test / GenElemInst_2`
- Direct property: `2134141914` changed from 30 to 40
- Derived property: `1473355128` changed from 72 to 77
- Differential report:
  [`codesys_diff_16_button_height.md`](codesys_diff_16_button_height.md)

With Y fixed at 57, the derived values satisfy `57 + 30 / 2 = 72` using
integer geometry and `57 + 40 / 2 = 77`. Together with experiment 14, this
independently supports the vertical-centre meaning. Repetition on another
rectangular control remains required before parser promotion.

## Experiment 17

- Baseline: `16_button_height.export`
- Variant: `17_button_text.export`
- Intended change: button text from Run Forward to Start Forward
- Direct property: `390574330` followed the text exactly
- Opaque property: `823443203` changed from 712 to 701
- Differential report:
  [`codesys_diff_17_button_text.md`](codesys_diff_17_button_text.md)

Property `823443203` also appears on other text-bearing elements, but its
values do not correspond directly to text length or geometry. It is retained
as a text-dependent derived value—possibly localization, layout, or another
internal key—without assigning a meaning.

## Experiment 18

- Baseline: `17_button_text.export`
- Variant: `18_button_binding.export`
- Intended change: Toggle binding from `PLC_PRG.xInp_PRunFwd` to
  `PLC_PRG.xInp_PStop`
- Numeric property changes: none
- Action before and after: Toggle
- Differential report:
  [`codesys_diff_18_button_binding.md`](codesys_diff_18_button_binding.md)

The binding is self-describing data within the configured Toggle action. It
does not require an opaque numeric property mapping, and the parser reports
the changed IEC operand directly.

## Experiment 19

- Baseline: `18_button_binding.export`
- Variant: `19_button_action.export`
- Intended change: remove the button's Toggle action
- Action: Toggle to absent
- Binding: `PLC_PRG.xInp_PStop` to absent
- Numeric property changes: none
- Differential report:
  [`codesys_diff_19_button_action.md`](codesys_diff_19_button_action.md)

The action owns its operand structurally. Removing the action removes the
binding without altering visual properties.

## Experiment 20

- Baseline: `19_button_action.export`
- Variant: `20_speed_format.export`
- Intended change: speed InputBox format from `%.2f` to `%.1f`
- Action property: `InputBox.Format` followed the editor value
- Binding and numeric property changes: none
- Differential report:
  [`codesys_diff_20_speed_format.md`](codesys_diff_20_speed_format.md)

The format is self-describing action data. TwinForge now reports individual
action-property transitions in a compact table rather than repeating the
complete action configuration.

## Experiment 21

- Baseline: `20_speed_format.export`
- Variant: `21_speed_limit.export`
- Intended change: speed InputBox maximum from 60 to 65
- Action property: `InputBox.InputBoxMax` changed from 60 to 65
- Binding, other action settings, and numeric properties: unchanged
- Differential report:
  [`codesys_diff_21_speed_limit.md`](codesys_diff_21_speed_limit.md)

The maximum is self-describing InputBox action data and does not require an
opaque visual-property mapping.

## Experiment 22

- Baseline: `21_speed_limit.export`
- Variant: `22_manager_style.export`
- Intended change: Visualization Manager style
- Before: `Basic style, 4.10.0.0 (CODESYS)`
- After: `CODESYS Demo Style, 4.0.0.0 (CODESYS GmbH)`
- Changed visual elements: none
- Differential report:
  [`codesys_diff_22_manager_style.md`](codesys_diff_22_manager_style.md)

The style is self-describing Visualization Manager data. Changing it does not
rewrite the controls' serialized visual-property maps.

## Experiment 23

- Baseline: `22_manager_style.export`
- Variant: `23_stop_button_x.export`
- Intended change: Stop button X position from 304 to 314
- Direct property: `1649127785` changed from 304 to 314
- Derived property: `550940142` changed from 379 to 389
- Fixed width: 150
- Differential report:
  [`codesys_diff_23_stop_button_x.md`](codesys_diff_23_stop_button_x.md)

Both derived values equal X plus half the width. This repeats experiment 13
on a second rectangular control and satisfies the local acceptance rule.
Property `550940142` is promoted to the CODESYS SP22 profile mapping
`center_x`; it is not claimed as universal across CODESYS profiles.

## Experiment 24

- Baseline: `23_stop_button_x.export`
- Variant: `24_stop_button_y.export`
- Intended change: Stop button Y position from 47 to 57
- Direct property: `357335551` changed from 47 to 57
- Derived property: `1473355128` changed from 62 to 72
- Fixed height: 30
- Differential report:
  [`codesys_diff_24_stop_button_y.md`](codesys_diff_24_stop_button_y.md)

Both derived values equal Y plus half the height. This repeats experiment 14
on a second rectangular control and satisfies the local acceptance rule.
Property `1473355128` is promoted to the CODESYS SP22 profile mapping
`center_y`; it is not claimed as universal across CODESYS profiles.

## Source-backed round-trip validation

- Source: `24_stop_button_y.export`
- Generated:
  `examples/CODESYS/25_powerflex_visualization_roundtrip.export`
- TwinForge semantic comparison: zero element and manager changes
- CODESYS profile: V3.5 SP22 Patch 2
- Import target: top Device
- Result: imported and rendered successfully

The rendered visualization retained the Start Forward text and enlarged
button, removed Start action, moved Stop button, speed-entry field, indicator,
logic-command display, and CODESYS Demo Style appearance.

## Deliberately modified export

- Source: `24_stop_button_y.export`
- Generated:
  `examples/CODESYS/26_powerflex_visualization_modified.export`
- Neutral control: `GenElemInst_2`
- Text: Start Forward to TwinForge Start
- X: 130 to 140
- Derived `center_x`: 210 to 220
- Other semantic changes: none
- Differential report:
  [`codesys_diff_26_modified.md`](codesys_diff_26_modified.md)

- CODESYS import target: top Device
- Result: imported successfully
- Rendered verification: TwinForge Start caption and modified X position
  confirmed

This verifies a deliberate neutral-model mutation through native CODESYS
export for the tested SP22 source-backed subset.
