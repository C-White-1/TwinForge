# Dvc_PF525 cyclic I/O contract

This report separates the drive-produced status image from the controller-produced command image. Field meanings come from captured datatype overlays; connection properties come from the associated module export.

## Connection

- Protocol: EtherNet/IP
- Requested packet interval: 10 ms
- Unicast: yes

## Input/status image

- AOI parameter: `Ref_DataIn`
- Parameter datatype: `AB:ETHERNET_MODULE_SINT_8Bytes:I:0`
- Connection point: 1
- Configured size: 8 bytes
- AOI copy size: 8 bytes
- Internal typed image: `Local.DataIn`

| Byte(s) | Bit | Field | Type | Meaning |
| --- | --- | --- | --- | --- |
| 0–3 | — | `Pad` | `DINT` | — |
| 4–5 | — | `DriveStatus` | `INT` | DriveStatus (overlay). |
| 4–5 | 0 | `Ready` | `BIT` | DriveStatus.0: Drive is ready for operation. |
| 4–5 | 1 | `Active` | `BIT` | DriveStatus.1: Drive is running. |
| 4–5 | 2 | `DirectionCmd` | `BIT` | DriveStatus.2: Drive commanded direction. |
| 4–5 | 3 | `Direction` | `BIT` | DriveStatus.3: Drive actual direction. |
| 4–5 | 4 | `Accelerating` | `BIT` | DriveStatus.4: Drive is accelerating. |
| 4–5 | 5 | `Decelerating` | `BIT` | DriveStatus.5: Drive is decelerating. |
| 4–5 | 6 | `DriveStatusBit6` | `BIT` | DS.6: Unused. |
| 4–5 | 7 | `Fault` | `BIT` | DriveStatus.7: Drive is faulted. |
| 4–5 | 8 | `AtSpeed` | `BIT` | DriveStatus.8: Drive is at commanded speed. |
| 4–5 | 9 | `ENetSpeedCtrl` | `BIT` | DriveStatus.9: Drive speed reference is provided over Ethernet. |
| 4–5 | 10 | `ENetLogicCtrl` | `BIT` | DriveStatus.10: Drive run and direction signals are provided over Ethernet. |
| 4–5 | 11 | `ParameterLock` | `BIT` | DriveStatus.11: Drive parameters are password-protected. |
| 4–5 | 12 | `DigIn5` | `BIT` | DriveStatus.12: State of digital input 5. |
| 4–5 | 13 | `DigIn6` | `BIT` | DriveStatus.13: State of digital input 6. |
| 4–5 | 14 | `DigIn7` | `BIT` | DriveStatus.14: State of digital input 7. |
| 4–5 | 15 | `DigIn8` | `BIT` | DriveStatus.15: State of digital input 8. |
| 6–7 | — | `OutputSpeed` | `INT` | — |

## Output/command image

- AOI parameter: `Ref_DataOut`
- Parameter datatype: `AB:ETHERNET_MODULE_SINT_4Bytes:O:0`
- Connection point: 2
- Configured size: 4 bytes
- AOI copy size: 4 bytes
- Internal typed image: `Local.DataOut`

| Byte(s) | Bit | Field | Type | Meaning |
| --- | --- | --- | --- | --- |
| 0–1 | — | `LogicCommand` | `INT` | LogicCommand (overlay). |
| 0–1 | 0 | `Stop` | `BIT` | LogicCommand.0: Stop. |
| 0–1 | 1 | `Start` | `BIT` | LogicCommand.1: Start. |
| 0–1 | 2 | `Jog` | `BIT` | LogicCommand.2: Jog. |
| 0–1 | 3 | `ClearFault` | `BIT` | LogicCommand.3: Clear fault. |
| 0–1 | 4 | `Forward` | `BIT` | LogicCommand.4: Forward. |
| 0–1 | 5 | `Reverse` | `BIT` | LogicCommand.5: Reverse. |
| 0–1 | 6 | `KeypadControl` | `BIT` | LogicCommand.6: Keypad control. |
| 0–1 | 7 | `MOPIncrement` | `BIT` | LogicCommand.7: MOP increment. |
| 0–1 | 8 | `AccelRate1` | `BIT` | LogicCommand.8: AccelRate1. |
| 0–1 | 9 | `AccelRate2` | `BIT` | LogicCommand.9: AccelRate2. |
| 0–1 | 10 | `DecelRate1` | `BIT` | LogicCommand.10: DecelRate1. |
| 0–1 | 11 | `DecelRate2` | `BIT` | LogicCommand.11: DecelRate2. |
| 0–1 | 12 | `FreqSel1` | `BIT` | LogicCommand.12: FreqSel1. |
| 0–1 | 13 | `FreqSel2` | `BIT` | LogicCommand.13: FreqSel2. |
| 0–1 | 14 | `FreqSel3` | `BIT` | LogicCommand.14: FreqSel3. |
| 0–1 | 15 | `MOPDecrement` | `BIT` | LogicCommand.15: MOP decrement. |
| 2–3 | — | `SpeedCommand` | `INT` | — |

## Operational interpretation

- The input connection image is consumed by the controller. The AOI ignores its leading four-byte `Pad` and interprets the following four bytes as drive status and speed feedback.
- The output assembly is produced by the controller and consumed by the drive as a logic command and speed reference.
- The AOI limits `LogicCommand` to `16#007F`; therefore bits 7–15 defined by the datatype are deliberately cleared by this implementation.
- `SpeedCommand` is written as frequency in hertz multiplied by 100, after clamping to zero and the captured maximum-speed limit. The transmitted integer therefore has 0.01 Hz/count.
- `OutputSpeed` is captured as a raw signed 16-bit cyclic feedback field. This AOI does not expose an observed scaling assignment for it, so TwinForge does not invent one.
