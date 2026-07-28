# Vendor-neutral visualization model

TwinForge separates authoring-system archives from visualization intent:

```text
CODESYS native archive
    -> lossless native parser
    -> exact profile property decoding
    -> vendor-neutral visualization model
    -> future target exporters
```

The neutral model is defined in
[`model/visualization.py`](../../src/twinforge/model/visualization.py). It
contains documents, canvases, controls, rectangular geometry, IEC expression
bindings, and portable interaction intents.

## Portable control categories

- Button
- Text input
- Indicator
- Label
- Unknown

The source control type is retained separately. An unfamiliar control is
therefore represented as `unknown` rather than discarded or forced into an
incorrect portable category.

## Binding and interaction semantics

Bindings distinguish value observation, command output, and user value input.
Interactions currently distinguish Toggle, value input, and unknown intents.
Value-input constraints normalize the source operand, format, minimum,
maximum, and prompt.

These concepts do not reference CODESYS object GUIDs, member IDs, dialog
libraries, PLCopen vendor extensions, or an OpenPLC implementation.

## Source preservation

The CODESYS converter is implemented in
[`converters/codesys_visualization.py`](../../src/twinforge/converters/codesys_visualization.py).
It retains source extensions at three levels:

- The complete native export on the neutral document
- The complete visualization archive entry on each canvas
- The complete native element and numeric-property map on each control

Interaction source XML is also retained. Unknown properties and actions are
never discarded.

For an exact verified profile, known numeric properties populate portable
geometry and text. For an unknown profile, the numeric map and raw XML remain
available while unverified portable fields stay absent. This prevents a future
CODESYS profile from silently inheriting SP22 serialization assumptions.

## Export boundary

The neutral model is suitable input for separate target adapters. A CODESYS
native exporter may use verified profile mappings and retained source
extensions. A future OpenPLC or web visualization exporter can use the
portable control and interaction intent without depending on the CODESYS
archive format.

## Source-backed CODESYS export

[`codesys_native_visualization.py`](../../src/twinforge/exporters/codesys_native_visualization.py)
exports by cloning the retained native archive and updating only verified
SP22 fields. It currently supports existing-control geometry, derived centre
coordinates, text, the selected theme, Toggle operands, and InputBox operand,
format, and limits.

It explicitly rejects archive synthesis, unknown profiles, canvas or control
addition/removal, control-type changes, interaction addition/removal, canvas
resize, and display-binding changes. Unknown nodes and numeric properties in
the retained archive pass through unchanged.

The generated `25_powerflex_visualization_roundtrip.export` was successfully
imported into CODESYS V3.5 SP22 Patch 2 by selecting the top Device as the
import target. CODESYS rendered the expected Start Forward and Stop controls,
speed entry, run indicator, command display, geometry, and selected Demo
style. This verifies source-backed unchanged round-trip compatibility for the
captured fixture.

The controlled modification example
[`modify_codesys_visualization.py`](../../examples/modify_codesys_visualization.py)
locates an existing neutral control and changes only explicitly supplied
geometry or text fields. The generated
`26_powerflex_visualization_modified.export` changes `GenElemInst_2` from
Start Forward to TwinForge Start and moves X from 130 to 140. TwinForge's
independent differential confirms the corresponding `center_x` change from
210 to 220 and no other semantic changes.

The modified export was subsequently imported successfully into CODESYS V3.5
SP22 Patch 2. CODESYS rendered the TwinForge Start caption at the modified X
position. This validates native generation for the documented source-backed,
verified-profile subset; it does not authorize synthetic archive creation or
unsupported structural mutations.

The controlled modifier also supports normalized value-input minimum, maximum,
format, and prompt fields. Export
`27_powerflex_speed_max_70.export` changes only
`GenElemInst_5`'s `InputBoxMax` from 65 to 70. The native differential reports
no binding, geometry, action-kind, control, or manager changes.

The export was imported successfully into CODESYS V3.5 SP22 Patch 2, where
the speed Textfield's input configuration reported a maximum of 70. This
verifies normalized InputBox-parameter generation for the tested source-backed
profile.

Export `28_powerflex_speed_prompt.export` experimentally changed only
`InputBoxDialogTitle` from `'Speed Setpoint (Hz)'` to
`'TwinForge Speed Setpoint (Hz)'`. CODESYS imported the field but its Default
Keypad continued to render `Speed Setpoint (Hz)`, while the independently
changed maximum of 70 remained effective. Prompt mutation is therefore not a
verified target capability and the exporter now rejects it.

Export `29_powerflex_speed_label.export` changes only the separate speed Label
control while leaving every InputBox property untouched. It is a controlled
test of whether the Default Keypad derives its runtime heading from nearby
label/localization evidence rather than `InputBoxDialogTitle`.

CODESYS rendered the modified label but retained the old keypad heading. The
direct-label hypothesis is therefore disproven.

A subsequent native CODESYS edit identified the required companion state:
changing the dialog title also changes `TextOutputVariableInitialized` from
False to True. The native edit produced the expected runtime heading.
TwinForge now emits both fields atomically when a neutral prompt changes.
Export `32_powerflex_prompt_initialized.export` reproduces exactly those two
action-property transitions.

Export 32 was imported and run successfully in CODESYS V3.5 SP22 Patch 2.
The Default Keypad displayed `TwinForge Speed Setpoint (Hz)`, and the widened
label rendered without clipping. This verifies prompt generation and its
required initialization state for the tested source-backed profile.

Because the longer experimental label was clipped at its original width,
export `30_powerflex_speed_label_wide.export` changes only that Label width
from 150 to 250 and updates its derived `center_x` from 195 to 245.
