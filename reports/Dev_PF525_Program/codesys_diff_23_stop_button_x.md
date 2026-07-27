# CODESYS visualization differential evidence

- Before profile: CODESYS V3.5 SP22 Patch 2
- After profile: CODESYS V3.5 SP22 Patch 2
- Changed elements: 1

## Element changes

### VISU_PowerFlex525_Test / GenElemInst_3

- Change: modified
- Type: Button

| Property ID | Known name | Before | After |
| --- | --- | --- | --- |
| 550940142 | center_x | 379 | 389 |
| 1649127785 | x | 304 | 314 |

- Bindings before: PLC_PRG.xInp_PStop
- Bindings after: PLC_PRG.xInp_PStop
- Actions before: Toggle
- Actions after: Toggle

## Visualization Manager changes

No manager changes were observed.

## Interpretation rule

An opaque property ID is not assigned a meaning from a single coincidence. A mapping becomes a candidate only when controlled exports vary one editor property at a time, and should be treated as profile-specific until repeated across CODESYS profiles.
