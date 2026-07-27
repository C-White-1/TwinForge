# CODESYS visualization inventory

- Profile: CODESYS V3.5 SP22 Patch 2
- Verified profile mappings: applied
- Visualizations: 1

## VISU_PowerFlex525_Test

- Canvas: 464 × 299
- Elements: 7

| ID | Identifier | Type | Geometry | Text | Bindings | Actions |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | GenElemInst_2 | Button | 130,57 160×40 | Start Forward | — | — |
| 3 | GenElemInst_3 | Button | 314,57 150×30 | Stop | PLC_PRG.xInp_PStop | Toggle |
| 5 | GenElemInst_5 | Textfield | 120,131 150×30 | — | PLC_PRG.rInp_PSpeed | InputBox |
| 7 | GenElemInst_7 | Lamp1 | 336,105 70×70 | — | PLC_PRG.xOut_RunFwd | — |
| 9 | GenElemInst_9 | Label | 120,171 150×30 | Speed Setpoint (Hz) | — | — |
| 11 | GenElemInst_11 | Textfield | 120,221 150×30 | Logic Command: %u | PLC_PRG.uiOut_LogicCommand | — |
| 13 | GenElemInst_12 | Label | 120,269 150×30 | Logic Command | — | — |

## Generation boundary

The native archive is profile-dependent and uses opaque numeric property identifiers. TwinForge preserves the complete source and raw element XML, but does not yet generate this format. Numeric property mappings must be verified against additional CODESYS exports before generation is considered safe.
