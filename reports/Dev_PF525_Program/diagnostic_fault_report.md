# Dvc diagnostic and fault report

Source implementation: `Dvc_PF525`. This is an offline evidence report; blank runtime values are not interpreted as healthy or fault-free.

## Live diagnostic contract

| Layer | Signal | Source | Meaning | Visible |
| --- | --- | --- | --- | :---: |
| drive | `Dvc_PF525.Sts_Fault` | `Local.DataIn.Fault` | Active drive fault | yes |
| communication | `Dvc_PF525.Sts_Connected` | `Module.Sts_Connected` | Module connection is established | no |
| communication | `Dvc_PF525.Sts_CommLoss` | `Module.Sts_Disconnected` | Module connection is disconnected | yes |
| drive | `Dvc_PF525.Sts_ResetReady` | `Local.Params.ResetReady` | Drive is faulted and the module connection is established | yes |
| module | `Sys_Module.Val_FaultCode` | `—` | A number that identifies a module fault, if one occurs. | yes |
| module | `Sys_Module.Val_FaultInfo` | `—` | Provides specific information about the Module object fault code. | yes |
| module | `Sys_Module.Sts_Faulted` | `Status.1` | Indicates whether any of the Module object’s connections to the associated module have failed. | yes |
| communication | `Sys_Module.Sts_Connected` | `Status.4` | All connections to the module are established and data is transferring. | yes |

## Communication-loss policies

| Parameter | Purpose | Offline configured value | Source |
| --- | --- | --- | --- |
| `C143` EN Comm Flt Actn | Selects the drive action when embedded EtherNet/IP communications are disrupted. Non-fault selections can permit continued operation and require commissioning verification. | `0` (Fault) | `Dvc.Cfg_ENetCommFaultAction` |
| `C144` EN Idle Flt Actn | Selects the drive action when the EtherNet/IP scanner becomes idle because the controller enters Program mode. Non-fault selections can permit continued operation and require commissioning verification. | `0` (Fault) | `Dvc.Cfg_ENetCommIdleAction` |

## Fault-history contract

Entry 1 is the most recent unique fault. Codes are paired with the captured operating snapshots below.

| Entry | Code | Frequency (Hz) | Current (A) | DC bus voltage (V DC) |
| ---: | --- | --- | --- | --- |
| 1 | `b007` | `F631` | `F641` | `F651` |
| 2 | `b008` | `F632` | `F642` | `F652` |
| 3 | `b009` | `F633` | `F643` | `F653` |
| 4 | `F604` | `F634` | `F644` | `F654` |
| 5 | `F605` | `F635` | `F645` | `F655` |
| 6 | `F606` | `F636` | `F646` | `F656` |
| 7 | `F607` | `F637` | `F647` | `F657` |
| 8 | `F608` | `F638` | `F648` | `F658` |
| 9 | `F609` | `F639` | `F649` | `F659` |
| 10 | `F610` | `F640` | `F650` | `F660` |

## Fault commands

### Reset active fault

- Sources: `PCmd_Reset, OCmd_Reset, MCmd_Reset, XCmd_Reset`
- Effect: Sets cyclic LogicCommand bit 3 (ClearFault).
- Evidence:

  - `Local.DataOut.ClearFault := PCmd_Reset OR OCmd_Reset OR MCmd_Reset OR XCmd_Reset;`

### Clear fault-history buffer

- Sources: `PCmd_ClearFaultBuffer, MCmd_ClearFaultBuffer`
- Effect: Requests A551 value 2 through the explicit write path.
- Evidence:

  - `Local.Params.FaultClear.SP := 2;`
  - `Local.Params.FaultClear.SP := 0;`
  - `if (Local.Params.FaultClear.SP <> Local.Params.FaultClear.PV & Local.Params.Fault01Code <> 0 & NOT Write) then`

## Important boundaries

- No online drive values were supplied; active fault codes and history contents are therefore unavailable.
- Logix module FaultCode and FaultInfo are controller-module diagnostics, not PowerFlex drive fault-history codes.
- Explicit-message ER status proves a message failure occurred but the AOI does not expose a decoded user-facing error catalogue.
- The commented F661–F670 fault-status snapshot requests are not active observations and are not reported as available values.
- The AOI exposes fault-code aliases Val_Fault01 through Val_Fault10; frequency, current, and DC-bus snapshots remain inside Local.Params rather than separate AOI output parameters.
