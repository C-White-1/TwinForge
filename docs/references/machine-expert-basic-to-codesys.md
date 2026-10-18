# Machine Expert – Basic to CODESYS: conversion table

This table answers one question for each part of an M221 program: what does
TwinForge do with it today?

Sources:

- **Objects and their behaviour:** Schneider's Generic Functions Library
  Guide (EIO0000003289) and M221 Programming Guide, installed with
  Machine Expert – Basic.
- **TwinForge's status:** its tests and the CODESYS and simulator runs, with
  links where each was established.
- **CODESYS rules:** [CODESYS PLCopen import rules](codesys-plcopen-import-rules.md),
  for how TwinForge must write things CODESYS accepts.

**Status key:**

| Status | Meaning |
| --- | --- |
| **Verified** | Converted, and its behaviour checked against the Machine Expert – Basic simulator and/or running in CODESYS. |
| **Converted** | Converted to an IEC equivalent with the same documented behaviour; tested by TwinForge, not yet on a simulator or controller. |
| **Declared only** | A variable is declared, but the M221 behaviour behind it is **not reproduced**. Reading it gives a value nothing updates. |
| **Not converted** | Kept as evidence: the rung becomes a comment with a diagnostic. |
| **Waiting** | Blocked on evidence: a fixture, or a CODESYS export to copy. |

A CODESYS equivalent marked *(candidate)* is a likely mapping that has not
been tried in CODESYS yet.

## Program structure

| Machine Expert – Basic | CODESYS | Status | Notes |
| --- | --- | --- | --- |
| Program POUs | Programs (LD) | Converted | Names made IEC-safe (`New POU` → `New_POU`). |
| Master task, freewheeling | Task `MAST`, Freewheeling | Verified | Ran in CODESYS (converted fixture 14). |
| Master task, periodic | Task `MAST`, Cyclic, `PeriodScan` ms | Converted | No sample uses period mode; the mapping follows the field names, unverified. |
| Periodic task (`FastTask`), events | Further tasks *(candidate)* | Not converted | |
| Ladder rungs (grid) | LD networks | Verified | All 264 sample grid rungs are equivalent to their IL. |
| Instruction List rungs | LD networks | Converted | All 94 IL-only sample rungs are ladder-expressible; any that are not keep their IL in a comment. |
| Grafcet (`%X` steps) | SFC *(candidate)* | Not converted | CODESYS's SFC is the IEC language that grew out of Grafcet; evolution rules differ in detail, so it needs checking like the counter and drum. TwinForge already writes SFC for CODESYS (Control Expert work). No sample uses Grafcet: needs a fixture. |
| Physical I/O addresses | I/O mapping, or `AT %IX...` | Waiting | I/O become variables; binding them to hardware needs CODESYS evidence. |

## Ladder elements

| Machine Expert – Basic | CODESYS | Status | Notes |
| --- | --- | --- | --- |
| Normally open/closed contact | Contact / negated contact | Verified | |
| Rising/falling edge contact | Contact with edge | Converted | |
| Coil, negated coil, set coil, reset coil | The same coils | Verified | Set coil ran in CODESYS (fixture 14). |
| Comparison box `[%MW0 > 10]` | IEC comparison function | Converted | Execution tests against the expression. |
| Operation box `[%MW1 := %MW1 + 1]` | IEC arithmetic functions | Converted | Execution tests; `%S18` overflow not modelled. |
| Shift functions `SHL`/`SHR`/`ROL`/`ROR` | IEC shift on `WORD`/`DWORD` | Converted | Execution tests against the guide's word shift. |
| `BTI`/`ITB` (BCD) | BCD conversion *(candidate)* | Waiting | No IEC name every target is evidenced to provide. |
| Timer preset write `%TM0.P := %MW0` | | Not converted | Needs a timer with a variable preset (4 sample boxes). |

## Language objects

| Object | M221 | CODESYS | Status | Notes |
| --- | --- | --- | --- | --- |
| `%I`, `%Q` | Digital I/O bits | `BOOL` variables | Converted | Named by symbol; unnamed ones get surrogates (`%I0.0` → `TF_I0_0`). Not bound to hardware (see above). |
| `%IW`, `%QW`, cartridge/extension analog | Analog I/O words | `INT` variables | Converted | Not bound to hardware. |
| `%M` | Memory bits | `BOOL` | Converted | Ordinary variables: on a warm start (power return with backup) the M221 keeps them, but a CODESYS Reset warm or runtime restart re-initialises them. RETAIN would match; not decided. The same applies to `%MW`, `%MD`, `%MF`. |
| `%MW`, `%MD`, `%MF` | Memory words | `INT`, `DINT`, `REAL` | Converted | |
| `%KW`, `%KD`, `%KF` | Constants | Constants *(candidate)* | **Declared only** | Typed where used, but their configured **values are not read**, so they read as 0. No sample or fixture configures one, so the format is unknown: needs a fixture. |
| `%TM` TON/TOF/TP | Timer | IEC `TON`/`TOF`/`TP` | Converted | `PT` = preset × time base; 50 of 54 sample timers. Behaviour per the guide, not simulator-checked. |
| `%TM` retentive | Retentive timer | `TONR` or Schneider's `FB_Timer` *(candidate)* | Not converted | Fixture `05c_timer`. |
| `%C` | Up/down counter, 0..9999 with wrap flags | `TF_MEBasic_Counter` | **Verified** | 16 recorded simulator checks; passes in CODESYS ([counter checks](../experiments/machine-expert-basic-counter-simulator.md)). |
| `%DR` | Drum sequencer | `TF_MEBasic_Drum` | **Verified** | 13 recorded simulator checks; passes in CODESYS; converted fixture 14 runs ([drum checks](../experiments/machine-expert-basic-drum-simulator.md)). Only drums the file configures. |
| `%R` | FIFO/LIFO register | Schneider's `FB_FiFo`/`FB_LiFo` show the shape *(candidate)* | Not converted | |
| `%SBR` | Shift bit register | `FB_ShiftBitRegister` shape *(candidate)* | Not converted | |
| `%SC` | Step counter | `FB_StepCounter` shape *(candidate)* | Not converted | |
| `%FC`, `%HSC`, `%PLS`, `%PWM` | Fast/high-speed counters, pulse outputs | Target hardware libraries | Not converted | Tied to the M221's hardware. |
| `%MSG`, `%WRITE_VAR`, `%READ_VAR` | Serial/Modbus communication | Target communication libraries | Not converted | No portable equivalent. |
| `%SCH` | Schedule blocks | | Not converted | |
| PID | PID controller (set up in Basic's PID assistant) | CODESYS Util library PID blocks *(candidate)* | Not converted | Needs its configuration read and the tuning parameters checked for equal meaning. No sample uses PID: needs a fixture. |

The *(candidate)* shapes for `%R`, `%SBR`, `%SC` and the retentive timer come
from Schneider's own TwidoEmulationSupport library
([notes](codesys-library-for-machine-expert-basic-blocks.md)), which exists
only inside Schneider's Machine Expert.

## System bits (`%S`)

The M221 drives or reads these; your program reads or sets them. Every
`.smbp` lists them all. TwinForge keeps them all in its model, but exports
**only those the converted logic uses** (since 2026-10-18). A used system
bit is **"Declared only"**, with a `runtime_object_not_driven` diagnostic
(nothing updates it), except the start bits `%S0`, `%S1`, `%S13`, the
clocks `%S4`–`%S7`, `%S50` and the real-time-clock words `%SW49`–`%SW53`,
which are reproduced (below, `runtime_object_reproduced` or
`system_event_binding_required`).

**Which are used in practice** (the 63 downloaded samples; 8 use any system
object at all):

| Samples | Objects |
| --- | --- |
| 3 | `%S13` first cycle; `%S0` cold start; `%S1` warm start |
| 1 each | `%S4`–`%S7` clocks; `%S9`; `%S12`; `%S14`–`%S20`; `%SW6`, `%SW7`, `%SW15`, `%SW16`, `%SW30`, `%SW70`, `%SW94` |

So the first to map are first cycle and cold/warm start, then the clocks.

| Bit | M221 meaning | CODESYS *(candidate)* |
| --- | --- | --- |
| `%S0`, `%S1` | Cold start, warm start (TRUE for the first scan) | **Verified.** Set by the same `TF_OnPrepareStart` from two flags in `TF_StartFlags`, one RETAIN: cold = download or Reset cold, warm = Reset warm or a runtime restart; cleared by `TF_EndOfScan` ([runs](../experiments/codesys-first-cycle.md)). |
| `%S4`–`%S7` | 10 ms, 100 ms, 1 s, 1 min square waves | **Verified** (1 s, 1 min measured). Set once per scan by `TF_StartOfScan`, called first in the task, from `TIME()`; the M221 changes them independently of the scan ([runs](../experiments/codesys-clocks-and-rtc.md)). |
| `%S9` | Apply fallback outputs | Device configuration, not a variable |
| `%S11` | Watchdog overflow | Task watchdog configuration |
| `%S12` | Controller running | Always TRUE while the program runs |
| `%S13` | First cycle after RUN | **Verified.** Set by `TF_OnPrepareStart`, a `PrepareStart` system-event handler, and cleared by `TF_EndOfScan`, called last in the task: TRUE for the first scan of every start, including stop → start. PLCopen cannot carry the event binding: after the import, run [`bind_system_events.py`](../../examples/CODESYS/scripts/bind_system_events.py) (diagnostic `system_event_binding_required`). CODESYS profile only ([runs](../experiments/codesys-first-cycle.md)). |
| `%S14`–`%S16` | Forcing active | None portable |
| `%S17`, `%S18`, `%S20`, `%S28` | Last bit shifted out, arithmetic overflow, index overflow, string overflow | None: IEC has no such flags |
| `%S19` | Scan period overrun | Task monitoring |
| `%S21`–`%S23` | Grafcet initialise, reset, freeze | SFC controls, if Grafcet is converted |
| `%S50` | Hold the RTC words so the program can write them | **Verified:** while TRUE, `TF_StartOfScan` leaves `%SW49`–`%SW53` alone. Setting the clock on its falling edge is **not converted** (on Control Win it would set the Windows clock). |
| `%S51`, `%S59` | Real-time clock status; adjust with `%SW59` | Not converted |
| `%S90`–`%S96` | Back up / restore memory words, program backup | Persistent (retain) variables |
| `%S32`–`%S36`, `%S101`–`%S115` | Ethernet, Modbus, ASCII, IO scanner | Target-specific, none portable |
| `%S106`, `%S107`, `%S119` | I/O bus behaviour, restart, local I/O error | Target-specific |
| `%S66`, `%S75` | Battery LED and status | Target-specific |
| `%S122`, `%S123` | Remote graphic display | None |

## System words (`%SW`)

Also exported only when used, with the same diagnostic, and **"Declared
only"** when they are.

| Words | M221 meaning | CODESYS *(candidate)* |
| --- | --- | --- |
| `%SW0`, `%SW1` | Master/periodic task period | Task configuration |
| `%SW11` | Software watchdog value | Task watchdog configuration |
| `%SW30`–`%SW32`, `%SW70`–`%SW72` | Last/max/min scan time (ms, µs) | Task information library |
| `%SW49`–`%SW53` | Real-time clock: day, seconds, hour:minute, month-day, year (BCD) | **Verified.** Local date and time from the SysTimeRtc library, in the M221's BCD words, set by `TF_StartOfScan` ([runs](../experiments/codesys-clocks-and-rtc.md)). |
| `%SW54`–`%SW58` | Date, time and code of the last stop | None portable |
| `%SW59` | Adjust current date | Real-time-clock library |
| `%SW75` | Processor load | Target-specific |
| `%SW76`–`%SW79` | Down counters 1–4 (counted down by the controller) | A timer in the program |
| `%SW6`, `%SW7`, `%SW118`, `%SW120` | Controller state and status, expansion module status | Target-specific |
| `%SW13`–`%SW16`, `%SW67`, `%SW107`–`%SW109`, `%SW115`–`%SW117` | Versions, controller type, MAC address, serial numbers | Target-specific |
| `%SW140`–`%SW147` | Last error codes, PLC log, SD card | Target-specific |
| `%SW62`–`%SW65`, `%SW98`–`%SW105`, `%SW121`, `%SW122`, `%SW168`–`%SW182` | Communication configuration, status and frame counters | Target-specific |
| `%SW39`–`%SW48`, `%SW130`–`%SW166` | Event and periodic task timing | Task information library |
| `%SW80`, `%SW128`, `%SW129`, `%SW139` | Analog input, cartridge and output-protection status | Target-specific |

## What would close the biggest gaps

1. **System objects:** done: only those a program uses are declared, each
   reported; first cycle `%S13` and cold/warm start `%S0`/`%S1` are
   reproduced, and so are the clocks `%S4`–`%S7` and reading the real-time
   clock. Next: setting the clock (`%S50`, `%S59`), on a test device.
   Related: on a warm start the M221 keeps all its data, CODESYS only
   RETAIN variables (see `%M` above).
2. **Constants (`%KW`/`%KD`/`%KF`):** a fixture with configured constants,
   to read their values.
3. **Physical I/O:** binding variables to CODESYS I/O (needs CODESYS
   evidence).
4. **Remaining function blocks:** retentive timer, shift bit register,
   FIFO/LIFO, step counter: the counter/drum route (simulator checks, then
   CODESYS).
