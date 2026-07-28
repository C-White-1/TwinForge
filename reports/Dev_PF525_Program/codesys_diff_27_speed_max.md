# CODESYS visualization differential evidence

- Before profile: CODESYS V3.5 SP22 Patch 2
- After profile: CODESYS V3.5 SP22 Patch 2
- Changed elements: 1

## Element changes

### VISU_PowerFlex525_Test / GenElemInst_5

- Change: modified
- Type: Textfield

| Property ID | Known name | Before | After |
| --- | --- | --- | --- |
| — | — | — | — |

- Bindings before: PLC_PRG.rInp_PSpeed
- Bindings after: PLC_PRG.rInp_PSpeed
- Actions before: InputBox
- Actions after: InputBox

| Action | Property | Before | After |
| --- | --- | --- | --- |
| InputBox | InputBoxMax | 65 | 70 |

## Visualization Manager changes

No manager changes were observed.

## Interpretation rule

An opaque property ID is not assigned a meaning from a single coincidence. A mapping becomes a candidate only when controlled exports vary one editor property at a time, and should be treated as profile-specific until repeated across CODESYS profiles.
