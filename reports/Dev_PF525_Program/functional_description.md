# Dvc functional description

## Scope and purpose

`Dvc_PF525` represents a PowerFlex 525 controller interface. Provide multi-source command arbitration, permissive and interlock gating, speed-reference handling, cyclic EtherNet/IP control, parameter access, and diagnostics for a variable-speed drive.

This document is generated from offline L5X and curated device-reference evidence. It describes observed software behavior and does not certify the implemented plant function.

## Communications

- Cyclic protocol: EtherNet/IP, RPI 10 ms
- Drive-to-controller image: connection point 1, 8 bytes
- Controller-to-drive image: connection point 2, 4 bytes
- Explicit parameter inventory: 163 observed parameter numbers

## Command-source modes

| Mode | Status | Speed source | Command behavior |
| --- | --- | --- | --- |
| Program | `Sts_Program` | PSet_Speed, or MSet_PSet while program-setpoint override is active | Level-triggered run; program stop removes the run request. |
| Operator | `Sts_Operator` | OSet_Speed | Latched run request from operator commands; separate stop required. |
| External | `Sts_External` | XSet_Speed | Latched run request from external commands; separate stop required. |
| Override | `Sts_Override` | OvSet_Speed | One encoded command selects no change, stop, forward, or reverse. |
| Maintenance | `Sts_Maintenance` | MSet_Speed | Latched maintenance run plus bypass and service commands. |
| Local or disabled | `Sts_Local / Sts_Disabled` | Drive-local source or no host reference | Host run and reverse requests are cleared by the fallback branch. |

## Functional behavior

### Initialization

Inhibition or an initialize command while stopped clears initialized status. While uninitialized, local status and edge-triggered command storage are reset. Initialization is restored after the parameter-read sequence completes.

Evidence:

- `if (Sts_Inhibited OR (PCmd_Initialize & NOT Sts_Active)) then`
- `if (NOT Sts_Initialized) then`
- `Sts_Initialized := 1;`

### Permissives and interlocks

Bypass may satisfy the bypassable permissive and interlock inputs. Non-bypassable permissives and interlocks always remain required. The executed interlock expression does not include the fault, EtherNet/IP logic-control, or safety-active terms shown inside its source comment.

Evidence:

- `PermOK := (Inp_PermOK OR Sts_Bypass) & Inp_NBPermOK;`
- `IntlkOK := (Inp_IntlkOK OR Sts_Bypass) & Inp_NBIntlkOK (*& NOT Sts_Fault & Sts_ENetLogicCtrl & NOT Sts_SafetyActive*);`
- `Sts_Bypass := (Sts_Bypass OR MCmd_EnableBypass) & NOT MCmd_DisableBypass;`

### Run and jog commands

Forward and reverse are mutually selected. Program run commands are level-triggered; operator, external, and maintenance starts are latched edge-style and require a separate stop. Jog commands require availability and permissive conditions.

Evidence:

- `RunFwd := PCmd_RunFwd & (PermOK OR RunFwd) & IntlkOK & NOT PCmd_Stop;`
- `RunFwd := (RunFwd OR (OCmd_RunFwd & Sts_RunFwdAvail & PermOK & NOT OCmd_RunRev)) & IntlkOK & NOT OCmd_Stop;`
- `JogFwd := Sts_JogFwdAvail & PermOK &`

### Start delay and audible request

A validated 0–60 second start delay is converted to milliseconds. Starting status follows timer timing, and the drive Start bit is withheld until the timer is done. When maintenance has enabled it, the audible request is active during the starting interval.

Evidence:

- `StartTimer.PRE := Cfg_StartDelay * 1000;`
- `Local.DataOut.Start := Sts_Ready & StartTimer.DN & NOT Local.DataOut.Stop & (RunFwd OR RunRev OR JogFwd OR JogRev);`
- `Out_Audible := Sts_AudibleEnabled & Sts_Starting;`

### Speed reference

The active command-source mode selects the speed reference. Jogging uses the configured jog speed. Negative requests are forced to zero, requests above maximum speed are limited, and the transmitted reference uses 0.01 Hz/count.

Evidence:

- `RefSpeed := PSet_Speed;`
- `Local.DataOut.SpeedCommand := RefSpeed * 100;`
- `Local.DataOut.SpeedCommand := Val_JogSpeed * 100;`

### Setpoint tracking

When set tracking is enabled, program mode tracks the operator setpoint from the active reference. Local mode tracks both operator and program setpoints from the reported command speed. The apparent operator-to-program tracking assignment is commented out.

Evidence:

- `if (Cfg_SetTrack) then`
- `OSet_Speed := RefSpeed;`
- `PSet_Speed := Val_CmdSpeed;`

### Parameter services

Cyclic operation is supplemented by explicit CIP reads and writes. Reads are enabled only while the module is connected and rotate through eight read sequences. Configured setpoints are compared with process values before individual writes are requested.

Evidence:

- `PG.Inp_Enable := Module.Sts_Connected;`
- `if (ReadSeq > 7) then`
- `if (Sts_Initialized & PG.Out) then`

## Status and diagnostics

- Live diagnostic indications: 8
- Configured communication-loss policies: 2
- Fault-history positions with observed parameter contracts: 10
- Active-fault reset uses cyclic LogicCommand bit 3; fault-history clearing uses explicit parameter A551 value 2.

## Engineering boundaries and verification

- This describes captured controller logic, not the complete mechanical, electrical, or process safety design.
- The AOI asserts that a safety function exists and derives SafetyActive from drive status, but no safety integrity claim can be made from L5X logic alone.
- The commented fault, EtherNet/IP-control, and safety terms in IntlkOK require manual design verification; see PF525-QA-020.
- Hardware behavior, parameter acceptance, timing, and network-loss response remain subject to commissioning tests.

Related generated evidence:

- `cyclic_io_contract.md`
- `diagnostic_fault_report.md`
- `parameter_setpoint_report.md` and its CSV companion
- `aoi_qa_issues.md`
