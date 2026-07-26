# PowerFlex 525 L5X evidence report

## Summary

- Documents: 3
- Controller workspaces: 1
- Candidate calls: 176
- Resolved software calls: 1
- Software/module assemblies: 1
- Assembled devices: 1
- Unassigned documents: 0
- Diagnostics: 0

## Documents

| Target type | Target name | Source file |
| --- | --- | --- |
| Module | Dev_PF525 | Dev_PF525_Module.L5X |
| Program | Dev_PF525 | Dev_PF525_Program.L5X |
| AddOnInstructionDefinition | Dvc_PF525 | Dvc_PF525_AOI.L5X |

## Controller workspaces

### DEVPAC

- Key: `context:DEVPAC`
- Evidence: `context_name_only`
- Confirmed by controller export: no
- Documents: `Dev_PF525_Module.L5X`, `Dev_PF525_Program.L5X`

## Resolved software calls

### `Dvc_PF525` in `Dev_PF525.Main`

- Source: `Dev_PF525_Program.L5X`
- Location: rung 3
- Instance tag: `Dvc`
- Source text: `Dvc_PF525(Dvc,Dev_PF525,Dev_PF525:I,Dev_PF525:O,ReadMsg,WriteMsg,MsgData,SysDevices)`

| Operand | Role | Parameter | Flow | Tag | Scope | Module | Module area |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dvc | instance | — | unknown | Dvc | program | — | — |
| Dev_PF525 | parameter | Ref_Module | in_out | — | — | Dev_PF525 | unknown |
| Dev_PF525:I | parameter | Ref_DataIn | in_out | — | — | Dev_PF525 | input |
| Dev_PF525:O | parameter | Ref_DataOut | in_out | — | — | Dev_PF525 | output |
| ReadMsg | parameter | Ref_ReadMsg | in_out | ReadMsg | program | — | — |
| WriteMsg | parameter | Ref_WriteMsg | in_out | WriteMsg | program | — | — |
| MsgData | parameter | Ref_MsgData | in_out | MsgData | program | — | — |
| SysDevices | parameter | Ref_Class | in_out | SysDevices | controller_context | — | — |

## Assembled devices

### Dvc

- Provider: `powerflex_525`
- Type: `drive`
- Manufacturer: Rockwell Automation
- Model: PowerFlex 525
- Modules: `Dev_PF525`
- Identity scopes: represented device identity is separate from controller module identity
  - Module `Dev_PF525` identity: Allen-Bradley / Rockwell Automation (controller representation)
- Interface: EtherNet/IP at `192.168.1.80`
  - Connection `Standard`: RPI 10000 µs, input 8 bytes, output 4 bytes, unicast yes
  - Service `ReadMsg`: `explicit_message_read`, code `0x32`, class `0x0093`, configured instance `0`, configured attribute `0x0000`
    - Configured transfer: 256 bytes via `Dev_PF525`; local `MsgData[0]`; destination `MsgData[0]`
    - Runtime mutable: yes; source `l5x_message_tag`
  - Service `WriteMsg`: `explicit_message_write`, code `0x10`, class `0x0093`, configured instance `34`, configured attribute `0x000A`
    - Configured transfer: 2 bytes via `Dev_PF525`; local `MsgData[64]`; destination `—`
    - Runtime mutable: yes; source `l5x_message_tag`
- Observed bulk-read parameter candidates (163): 1–9, 12–17, 19–22, 27–29, 31–51, 53, 62–70, 72–73, 75–77, 79–82, 84–85, 88, 90, 99, 105–106, 143–144, 360–364, 367, 369, 375–376, 378, 380–382, 393–394, 431–432, 434–435, 439–441, 486–487, 490–491, 534–537, 543–548, 550–551, 555, 559, 572, 575–576, 604–610, 631–660, 693–704
- Observed write parameter candidates (70): 31–39, 41–51, 53, 62–70, 72–73, 75–77, 79–82, 84–85, 88, 90, 99, 105–106, 143–144, 431–432, 434–435, 439, 441, 486–487, 490–491, 534–537, 543–546, 548, 551, 559, 572
- Parameter groups: Advanced Display (15), Advanced Program (28), Basic Display (22), Basic Program (22), Communications (2), Fault and Diagnostic (49), Terminal Block (25)
- Parameter references: Rockwell Automation Publication 520-UM001L-EN-E, PowerFlex 520-Series Adjustable Frequency AC Drive User Manual, March 2022

Observed parameter inventory:

| Number | Code | Name | Group | Read | Write | Read buffer slots |
| ---: | --- | --- | --- | :---: | :---: | --- |
| 1 | b001 | Output Freq | Basic Display | yes | no | 0 |
| 2 | b002 | Commanded Freq | Basic Display | yes | no | 1 |
| 3 | b003 | Output Current | Basic Display | yes | no | 2 |
| 4 | b004 | Output Voltage | Basic Display | yes | no | 3 |
| 5 | b005 | DC Bus Voltage | Basic Display | yes | no | 4 |
| 6 | b006 | Drive Status | Basic Display | yes | no | 5 |
| 7 | b007 | Fault 1 Code | Basic Display | yes | no | 6 |
| 8 | b008 | Fault 2 Code | Basic Display | yes | no | 7 |
| 9 | b009 | Fault 3 Code | Basic Display | yes | no | 8 |
| 12 | b012 | Control Source | Basic Display | yes | no | 9 |
| 13 | b013 | Control Input Status | Basic Display | yes | no | 10 |
| 14 | b014 | Digital Input Status | Basic Display | yes | no | 11 |
| 15 | b015 | Output RPM | Basic Display | yes | no | 12 |
| 16 | b016 | Output Speed | Basic Display | yes | no | 13 |
| 17 | b017 | Output Power | Basic Display | yes | no | 14 |
| 19 | b019 | Elapsed Run Time | Basic Display | yes | no | 1 |
| 20 | b020 | Average Power | Basic Display | yes | no | 2 |
| 21 | b021 | Elapsed kWh | Basic Display | yes | no | 3 |
| 22 | b022 | Elapsed MWh | Basic Display | yes | no | 4 |
| 27 | b027 | Drive Temp | Basic Display | yes | no | 15 |
| 28 | b028 | Control Temp | Basic Display | yes | no | 16 |
| 29 | b029 | Control SW Version | Basic Display | yes | no | 9 |
| 31 | P031 | Motor NP Volts | Basic Program | yes | yes | 10 |
| 32 | P032 | Motor NP Hertz | Basic Program | yes | yes | 11 |
| 33 | P033 | Motor OL Current | Basic Program | yes | yes | 12 |
| 34 | P034 | Motor NP FLA | Basic Program | yes | yes | 13 |
| 35 | P035 | Motor NP Poles | Basic Program | yes | yes | 14 |
| 36 | P036 | Motor NP RPM | Basic Program | yes | yes | 15 |
| 37 | P037 | Motor NP Power | Basic Program | yes | yes | 16 |
| 38 | P038 | Voltage Class | Basic Program | yes | yes | 17 |
| 39 | P039 | Torque Perf Mode | Basic Program | yes | yes | 18 |
| 40 | P040 | Autotune | Basic Program | yes | no | 17 |
| 41 | P041 | Accel Time 1 | Basic Program | yes | yes | 18 |
| 42 | P042 | Decel Time 1 | Basic Program | yes | yes | 19 |
| 43 | P043 | Minimum Freq | Basic Program | yes | yes | 20 |
| 44 | P044 | Maximum Freq | Basic Program | yes | yes | 21 |
| 45 | P045 | Stop Mode | Basic Program | yes | yes | 22 |
| 46 | P046 | Start Source 1 | Basic Program | yes | yes | 23 |
| 47 | P047 | Speed Reference 1 | Basic Program | yes | yes | 24 |
| 48 | P048 | Start Source 2 | Basic Program | yes | yes | 19 |
| 49 | P049 | Speed Reference 2 | Basic Program | yes | yes | 20 |
| 50 | P050 | Start Source 3 | Basic Program | yes | yes | 21 |
| 51 | P051 | Speed Reference 3 | Basic Program | yes | yes | 22 |
| 53 | P053 | Reset To Defaults | Basic Program | yes | yes | 25 |
| 62 | T062 | DigIn TermBlk 02 | Terminal Block | yes | yes | 24 |
| 63 | T063 | DigIn TermBlk 03 | Terminal Block | yes | yes | 25 |
| 64 | T064 | 2-Wire Mode | Terminal Block | yes | yes | 26 |
| 65 | T065 | DigIn TermBlk 05 | Terminal Block | yes | yes | 27 |
| 66 | T066 | DigIn TermBlk 06 | Terminal Block | yes | yes | 28 |
| 67 | T067 | DigIn TermBlk 07 | Terminal Block | yes | yes | 29 |
| 68 | T068 | DigIn TermBlk 08 | Terminal Block | yes | yes | 30 |
| 69 | T069 | Opto Out1 Sel | Terminal Block | yes | yes | 31 |
| 70 | T070 | Opto Out1 Level | Terminal Block | yes | yes | 26 |
| 72 | T072 | Opto Out2 Sel | Terminal Block | yes | yes | 32 |
| 73 | T073 | Opto Out2 Level | Terminal Block | yes | yes | 27 |
| 75 | T075 | Opto Out Logic | Terminal Block | yes | yes | 33 |
| 76 | T076 | Relay Out1 Sel | Terminal Block | yes | yes | 34 |
| 77 | T077 | Relay Out1 Level | Terminal Block | yes | yes | 28 |
| 79 | T079 | Relay 1 On Time | Terminal Block | yes | yes | 35 |
| 80 | T080 | Relay 1 Off Time | Terminal Block | yes | yes | 36 |
| 81 | T081 | Relay Out2 Sel | Terminal Block | yes | yes | 37 |
| 82 | T082 | Relay Out2 Level | Terminal Block | yes | yes | 29 |
| 84 | T084 | Relay 2 On Time | Terminal Block | yes | yes | 38 |
| 85 | T085 | Relay 2 Off Time | Terminal Block | yes | yes | 39 |
| 88 | T088 | Analog Out Sel | Terminal Block | yes | yes | 42 |
| 90 | T090 | Analog Out Setpoint | Terminal Block | yes | yes | 30 |
| 99 | T099 | Analog In Filter | Terminal Block | yes | yes | 52 |
| 105 | T105 | Safety Open Enable | Terminal Block | yes | yes | 58 |
| 106 | T106 | Safety Fault Reset Configuration | Terminal Block | yes | yes | 59 |
| 143 | C143 | EN Comm Flt Actn | Communications | yes | yes | 0 |
| 144 | C144 | EN Idle Flt Actn | Communications | yes | yes | 1 |
| 360 | d360 | AnalogIn0-10V | Advanced Display | yes | no | 31 |
| 361 | d361 | AnalogIn4-20mA | Advanced Display | yes | no | 32 |
| 362 | d362 | ElapsedTimeHr | Advanced Display | yes | no | 2 |
| 363 | d363 | ElapsedTimeMin | Advanced Display | yes | no | 3 |
| 364 | d364 | CounterStatus | Advanced Display | yes | no | 33 |
| 367 | d367 | DriveType | Advanced Display | yes | no | 4 |
| 369 | d369 | MotorOLLevel | Advanced Display | yes | no | 35 |
| 375 | d375 | SlipHzMeter | Advanced Display | yes | no | 36 |
| 376 | d376 | SpeedFeedback | Advanced Display | yes | no | 37 |
| 378 | d378 | EncoderSpeed | Advanced Display | yes | no | 38 |
| 380 | d380 | DCBusRipple | Advanced Display | yes | no | 39 |
| 381 | d381 | OutputPowerFactor | Advanced Display | yes | no | 40 |
| 382 | d382 | TorqueCurrent | Advanced Display | yes | no | 41 |
| 393 | d393 | DriveStatus2 | Advanced Display | yes | no | 46 |
| 394 | d394 | DigOutStatus | Advanced Display | yes | no | 47 |
| 431 | A431 | JogFrequency | Advanced Program | yes | yes | 11 |
| 432 | A432 | JogAccelDecel | Advanced Program | yes | yes | 12 |
| 434 | A434 | DCBrakeTime | Advanced Program | yes | yes | 14 |
| 435 | A435 | DCBrakeLevel | Advanced Program | yes | yes | 15 |
| 439 | A439 | SCurvePercent | Advanced Program | yes | yes | 19 |
| 440 | A440 | PWMFrequency | Advanced Program | yes | no | 20 |
| 441 | A441 | DroopHertzFLA | Advanced Program | yes | yes | 21 |
| 486 | A486 | ShearPin1Level | Advanced Program | yes | yes | 33 |
| 487 | A487 | ShearPin1Time | Advanced Program | yes | yes | 34 |
| 490 | A490 | LoadLossLevel | Advanced Program | yes | yes | 37 |
| 491 | A491 | LoadLossTime | Advanced Program | yes | yes | 38 |
| 534 | A534 | MaximumVoltage | Advanced Program | yes | yes | 13 |
| 535 | A535 | MotorFeedbackType | Advanced Program | yes | yes | 14 |
| 536 | A536 | EncoderPPR | Advanced Program | yes | yes | 15 |
| 537 | A537 | PulseInScale | Advanced Program | yes | yes | 16 |
| 543 | A543 | StartAtPowerUp | Advanced Program | yes | yes | 22 |
| 544 | A544 | ReverseDisable | Advanced Program | yes | yes | 23 |
| 545 | A545 | FlyingStartEnable | Advanced Program | yes | yes | 24 |
| 546 | A546 | FlyStrtCurLimit | Advanced Program | yes | yes | 25 |
| 547 | A547 | Compensation | Advanced Program | yes | no | 26 |
| 548 | A548 | PowerLossMode | Advanced Program | yes | yes | 27 |
| 550 | A550 | BusRegEnable | Advanced Program | yes | no | 29 |
| 551 | A551 | FaultClear | Advanced Program | yes | yes | 48 |
| 555 | A555 | ResetMeters | Advanced Program | yes | no | 51 |
| 559 | A559 | CountsPerUnit | Advanced Program | yes | yes | 33 |
| 572 | A572 | SpeedRatio | Advanced Program | yes | yes | 46 |
| 575 | A575 | FluxBrakingEn | Advanced Program | yes | no | 49 |
| 576 | A576 | PhaseLossLevel | Advanced Program | yes | no | 50 |
| 604 | F604 | Fault04Code | Fault and Diagnostic | yes | no | 61 |
| 605 | F605 | Fault05Code | Fault and Diagnostic | yes | no | 62 |
| 606 | F606 | Fault06Code | Fault and Diagnostic | yes | no | 63 |
| 607 | F607 | Fault07Code | Fault and Diagnostic | yes | no | 0 |
| 608 | F608 | Fault08Code | Fault and Diagnostic | yes | no | 1 |
| 609 | F609 | Fault09Code | Fault and Diagnostic | yes | no | 2 |
| 610 | F610 | Fault10Code | Fault and Diagnostic | yes | no | 3 |
| 631 | F631 | Fault01Speed | Fault and Diagnostic | yes | no | 4 |
| 632 | F632 | Fault02Speed | Fault and Diagnostic | yes | no | 5 |
| 633 | F633 | Fault03Speed | Fault and Diagnostic | yes | no | 6 |
| 634 | F634 | Fault04Speed | Fault and Diagnostic | yes | no | 7 |
| 635 | F635 | Fault05Speed | Fault and Diagnostic | yes | no | 8 |
| 636 | F636 | Fault06Speed | Fault and Diagnostic | yes | no | 9 |
| 637 | F637 | Fault07Speed | Fault and Diagnostic | yes | no | 10 |
| 638 | F638 | Fault08Speed | Fault and Diagnostic | yes | no | 11 |
| 639 | F639 | Fault09Speed | Fault and Diagnostic | yes | no | 12 |
| 640 | F640 | Fault10Speed | Fault and Diagnostic | yes | no | 13 |
| 641 | F641 | Fault01Current | Fault and Diagnostic | yes | no | 14 |
| 642 | F642 | Fault02Current | Fault and Diagnostic | yes | no | 15 |
| 643 | F643 | Fault03Current | Fault and Diagnostic | yes | no | 16 |
| 644 | F644 | Fault04Current | Fault and Diagnostic | yes | no | 17 |
| 645 | F645 | Fault05Current | Fault and Diagnostic | yes | no | 18 |
| 646 | F646 | Fault06Current | Fault and Diagnostic | yes | no | 19 |
| 647 | F647 | Fault07Current | Fault and Diagnostic | yes | no | 20 |
| 648 | F648 | Fault08Current | Fault and Diagnostic | yes | no | 21 |
| 649 | F649 | Fault09Current | Fault and Diagnostic | yes | no | 22 |
| 650 | F650 | Fault10Current | Fault and Diagnostic | yes | no | 23 |
| 651 | F651 | Fault01BusVoltage | Fault and Diagnostic | yes | no | 24 |
| 652 | F652 | Fault02BusVoltage | Fault and Diagnostic | yes | no | 25 |
| 653 | F653 | Fault03BusVoltage | Fault and Diagnostic | yes | no | 26 |
| 654 | F654 | Fault04BusVoltage | Fault and Diagnostic | yes | no | 27 |
| 655 | F655 | Fault05BusVoltage | Fault and Diagnostic | yes | no | 28 |
| 656 | F656 | Fault06BusVoltage | Fault and Diagnostic | yes | no | 29 |
| 657 | F657 | Fault07BusVoltage | Fault and Diagnostic | yes | no | 30 |
| 658 | F658 | Fault08BusVoltage | Fault and Diagnostic | yes | no | 31 |
| 659 | F659 | Fault09BusVoltage | Fault and Diagnostic | yes | no | 32 |
| 660 | F660 | Fault10BusVoltage | Fault and Diagnostic | yes | no | 33 |
| 693 | F693 | IPAddr1 | Fault and Diagnostic | yes | no | 52 |
| 694 | F694 | IPAddr2 | Fault and Diagnostic | yes | no | 53 |
| 695 | F695 | IPAddr3 | Fault and Diagnostic | yes | no | 54 |
| 696 | F696 | IPAddr4 | Fault and Diagnostic | yes | no | 55 |
| 697 | F697 | IPMask1 | Fault and Diagnostic | yes | no | 56 |
| 698 | F698 | IPMask2 | Fault and Diagnostic | yes | no | 57 |
| 699 | F699 | IPMask3 | Fault and Diagnostic | yes | no | 58 |
| 700 | F700 | IPMask4 | Fault and Diagnostic | yes | no | 59 |
| 701 | F701 | IPGateway1 | Fault and Diagnostic | yes | no | 60 |
| 702 | F702 | IPGateway2 | Fault and Diagnostic | yes | no | 61 |
| 703 | F703 | IPGateway3 | Fault and Diagnostic | yes | no | 62 |
| 704 | F704 | IPGateway4 | Fault and Diagnostic | yes | no | 63 |

Curated parameter semantics:

| Code | Purpose | Range, options, or flags | Units | Default | Resolution | Access | Stop required |
| --- | --- | --- | --- | --- | --- | --- | :---: |
| b001 | Reports output frequency at motor terminals T1, T2, and T3, excluding slip frequency. | 0.00 to P044 Maximum Freq | Hz | — | 0.01 Hz | Read only | no |
| b002 | Reports the active frequency command whether or not the drive is running. | 0.00 to P044 Maximum Freq | Hz | — | 0.01 Hz | Read only | no |
| b003 | Reports output current at motor terminals T1, T2, and T3. | 0.00 to Drive Rated Amps × 2 | A | — | 0.01 A | Read only | no |
| b004 | Reports output voltage at motor terminals T1, T2, and T3. | 0.0 to Drive Rated Volts | V | — | 0.1 V | Read only | no |
| b005 | Reports the filtered drive DC-bus voltage. | 0 to 1200 | V DC | — | 1 V DC | Read only | no |
| b006 | Reports the present drive operating condition as active flags. | Digit 1 = Running; Digit 2 = Forward; Digit 3 = Accelerating; Digit 4 = Decelerating; Digit 5 = Safety Active | — | — | — | Read only | no |
| b007 | Reports the first entry in the unique recent-fault history, with Fault 1 being the most recent. | F0 to F127 | — | — | — | Read only | no |
| b008 | Reports the second entry in the unique recent-fault history, with Fault 1 being the most recent. | F0 to F127 | — | — | — | Read only | no |
| b009 | Reports the third entry in the unique recent-fault history, with Fault 1 being the most recent. | F0 to F127 | — | — | — | Read only | no |
| b012 | Reports the active start-command and frequency-command sources as encoded decimal digits. | Digit 1 Start command source: 1=Keypad, 2=Digital Input Terminal Block, 3=Serial/DSI, 4=Network Option, 5=EtherNet/IP; Digits 2–3 Frequency command source: 00=Other, 01=Drive Potentiometer, 02=Keypad Frequency, 03=Serial/DSI, 04=Network Option, 05=0–10 V Input, 06=4–20 mA Input, 07=Preset Frequency, 08=Analog Input Multiply, 09=MOP, 10=Pulse Input, 11=PID1 Output, 12=PID2 Output, 13=Step Logic, 14=Encoder, 15=EtherNet/IP, 16=Positioning; Digit 4 Frequency override: 0=Other, 1=Jog, 2=Purge | — | — | — | Read only | no |
| b013 | Reports terminal-block inputs 1 through 3 and the dynamic-brake transistor state. | Digit 1 = Terminal 1 Closed; Digit 2 = Terminal 2 Closed; Digit 3 = Terminal 3 Closed; Digit 4 = Dynamic-Brake Transistor On | — | — | — | Read only | no |
| b014 | Reports the state of programmable digital inputs 5–8. | Digit 1 = Terminal 5 Closed; Digit 2 = Terminal 6 Closed; Digit 3 = Terminal 7 Closed; Digit 4 = Terminal 8 Closed | — | — | — | Read only | no |
| b015 | Reports output frequency converted to rotational speed using P035 Motor NP Poles. | 0 to 24000 | rpm | — | 1 rpm | Read only | no |
| b016 | Reports output frequency as a percentage of P044 Maximum Freq. | 0.0 to 100.0 | % | — | 0.1% | Read only | no |
| b017 | Reports output power at motor terminals T1, T2, and T3. | 0.00 to Drive Rated Power × 2 | kW | — | 0.01 kW | Read only | no |
| b019 | Reports accumulated time during which the drive has been outputting power. | 0 to 65535 × 10 | h | — | 10 h | Read only | no |
| b020 | Reports average motor power since the energy meters were last reset. | 0.00 to Drive Rated Power × 2 | kW | — | 0.01 kW | Read only | no |
| b021 | Reports accumulated output energy; at 100.0 kWh it resets and increments b022 Elapsed MWh. | 0.0 to 100.0 | kWh | — | 0.1 kWh | Read only | no |
| b022 | Reports accumulated drive output energy in megawatt-hours. | 0.0 to 6553.5 | MWh | — | 0.1 MWh | Read only | no |
| b027 | Reports the present operating temperature of the drive heatsink. | 0 to 120 | °C | — | 1 °C | Read only | no |
| b028 | Reports the present operating temperature of the drive control. | 0 to 120 | °C | — | 1 °C | Read only | no |
| b029 | Reports the current drive firmware revision. | 0.000 to 65.535 | — | — | 0.001 | Read only | no |
| P031 | Sets the motor nameplate rated voltage. | 10 (230 V drives), 20 (460 V drives), or 25 (600 V drives) to Drive Rated Volts | V | Drive Rated Volts | 1 V | Read/write | yes |
| P032 | Sets the motor nameplate rated frequency. | 15 to 500 | Hz | 60 | 1 Hz | Read/write | yes |
| P033 | Sets the motor nameplate overload current used to determine motor overload conditions. | 0.0 to Drive Rated Amps × 2 | A | Drive Rated Amps | 0.1 A | Read/write | no |
| P034 | Sets the motor nameplate full-load current used by autotune and motor control. | 0.1 to Drive Rated Amps × 2 | A | Based on Drive Rating | 0.1 A | Read/write | no |
| P035 | Sets the number of poles in the motor. | 2 to 40 | — | 4 | 1 | Read/write | no |
| P036 | Sets the rated motor nameplate speed used to calculate rated slip. | 0 to 24000 | rpm | 1750 | 1 rpm | Read/write | yes |
| P037 | Sets the motor nameplate power used by the PM regulator. | 0.00 to Drive Rated Power | kW | Drive Rated Power | 0.01 kW | Read/write | no |
| P038 | Sets the voltage class of 600 V drives. | 2 = Low Voltage (480 V); 3 = High Voltage (600 V) | — | 3 | — | Read/write | yes |
| P039 | Selects the motor control mode. | 0 = V/Hz; 1 = SVC; 2 = Economize; 3 = Vector; 4 = PM Control; 5 = SynRM | — | 1 | — | Read/write | yes |
| P040 | Initiates a static or rotational autotune and returns to Ready/Idle when complete. | 0 = Ready/Idle; 1 = Static Tune; 2 = Rotate Tune | — | 0 | — | Read/write | yes |
| P041 | Sets the time to accelerate from 0 Hz to P044 Maximum Freq. | 0.00 to 600.00 | s | 10.00 | 0.01 s | Read/write | no |
| P042 | Sets the time to decelerate from P044 Maximum Freq to 0 Hz. | 0.00 to 600.00 | s | 10.00 | 0.01 s | Read/write | no |
| P043 | Sets the lowest frequency the drive outputs. | 0.00 to 500.00 | Hz | 0.00 | 0.01 Hz | Read/write | yes |
| P044 | Sets the highest frequency the drive outputs. | 0.00 to 500.00 | Hz | 60.00 | 0.01 Hz | Read/write | yes |
| P045 | Selects the stopping mode used when a stop is initiated. | 0 = Ramp, CF; 1 = Coast, CF; 2 = DC Brake, CF; 3 = DC BrkAuto,CF; 4 = Ramp; 5 = Coast; 6 = DC Brake; 7 = DC BrakeAuto; 8 = Ramp+EM B,CF; 9 = Ramp+EM Brk; 10 = PointStp,CF; 11 = PointStop | — | 0 | — | Read/write | no |
| P046 | Selects the primary start-command source. | See option set: Start Source | — | 1 | — | Read/write | yes |
| P047 | Selects the primary speed-command source. | See option set: Speed Reference | — | 1 | — | Read/write | no |
| P048 | Selects the second start-command source. | See option set: Start Source | — | 2 | — | Read/write | yes |
| P049 | Selects the second speed-command source. | See option set: Speed Reference | — | 5 | — | Read/write | no |
| P050 | Selects the third start-command source. | See option set: Start Source | — | 5 | — | Read/write | yes |
| P051 | Selects the third speed-command source. | See option set: Speed Reference | — | 15 | — | Read/write | no |
| P053 | Issues a parameter, factory, power-parameter, or module reset and then returns to Ready/Idle. | 0 = Ready/Idle; 1 = Param Reset; 2 = Factory Reset; 3 = Power Reset; 4 = Module Reset | — | 0 | — | Read/write | yes |
| T062 | Assigns the function of digital input terminal 02; some choices are terminal-specific or may be assigned to only one input. | See option set: Programmable Digital Input | — | 48 | — | Read/write | yes |
| T063 | Assigns the function of digital input terminal 03; some choices are terminal-specific or may be assigned to only one input. | See option set: Programmable Digital Input | — | 50 | — | Read/write | yes |
| T064 | Selects the trigger mode for terminals 02 and 03 when a two-wire start source is used. Level Sense can restart when a maintained Run input remains active. | 0 = Edge Trigger; 1 = Level Sense; 2 = High-Speed Edge; 3 = Momentary | — | 0 | — | Read/write | yes |
| T065 | Assigns the function of digital input terminal 05; some choices are terminal-specific or may be assigned to only one input. | See option set: Programmable Digital Input | — | 7 | — | Read/write | yes |
| T066 | Assigns the function of digital input terminal 06; some choices are terminal-specific or may be assigned to only one input. | See option set: Programmable Digital Input | — | 7 | — | Read/write | yes |
| T067 | Assigns the function of digital input terminal 07; some choices are terminal-specific or may be assigned to only one input. | See option set: Programmable Digital Input | — | 5 | — | Read/write | yes |
| T068 | Assigns the function of digital input terminal 08; some choices are terminal-specific or may be assigned to only one input. | See option set: Programmable Digital Input | — | 9 | — | Read/write | yes |
| T069 | Selects the condition that changes opto output 1 state. | See option set: Programmable Digital Output | — | 2 | — | Read/write | no |
| T070 | Sets the opto output 1 switching threshold or direct control value; its units and valid range depend on T069. | 0.0 to 9999.0 | — | 0.0 | 0.1 | Read/write | no |
| T072 | Selects the condition that changes opto output 2 state. | See option set: Programmable Digital Output | — | 1 | — | Read/write | no |
| T073 | Sets the opto output 2 switching threshold or direct control value; its units and valid range depend on T072. | 0.0 to 9999.0 | — | 0.0 | 0.1 | Read/write | no |
| T075 | Selects normally-open or normally-closed logic independently for the two opto outputs. | 0 = Output 1 NO; Output 2 NO; 1 = Output 1 NC; Output 2 NO; 2 = Output 1 NO; Output 2 NC; 3 = Output 1 NC; Output 2 NC | — | 0 | — | Read/write | no |
| T076 | Selects the condition that changes relay output 1 state. | See option set: Programmable Digital Output | — | 0 | — | Read/write | no |
| T077 | Sets the relay output 1 switching threshold or direct control value; its units and valid range depend on T076. | 0.0 to 9999.0 | — | 0.0 | 0.1 | Read/write | no |
| T079 | Sets the delay before relay 1 energizes after its selected condition is met. | 0.0 to 600.0 | s | 0.0 | 0.1 s | Read/write | no |
| T080 | Sets the delay before relay 1 de-energizes after its selected condition ceases. | 0.0 to 600.0 | s | 0.0 | 0.1 s | Read/write | no |
| T081 | Selects the condition that changes relay output 2 state. | See option set: Programmable Digital Output | — | 2 | — | Read/write | no |
| T082 | Sets the relay output 2 switching threshold or direct control value; its units and valid range depend on T081. | 0.0 to 9999.0 | — | 0.0 | 0.1 | Read/write | no |
| T084 | Sets the delay before relay 2 energizes after its selected condition is met. | 0.0 to 600.0 | s | 0.0 | 0.1 s | Read/write | no |
| T085 | Sets the delay before relay 2 de-energizes after its selected condition ceases. | 0.0 to 600.0 | s | 0.0 | 0.1 s | Read/write | no |
| T088 | Selects the drive quantity and electrical range represented by the analog output. | See option set: Analog Output Selection | — | 0 | — | Read/write | no |
| T090 | Sets the requested analog-output percentage when T088 selects setpoint mode 6, 14, or 22. | 0.0 to 100.0 | % | 0.0 | 0.1% | Read/write | no |
| T099 | Selects additional analog-input filtering; each increment doubles the applied filtering and reduces bandwidth. | 0 to 14 | — | 0 | 1 | Read/write | no |
| T105 | Selects whether the drive faults when both safe-torque-off inputs are de-energized. | 0 = Fault Enable; 1 = Fault Disable | — | 0 | — | Read/write | no |
| T106 | Selects whether safety hardware fault F111 is reset by a power cycle or by the fault-clear mechanism. | 0 = Power-Cycle Reset; 1 = Fault-Clear Reset | — | 0 | — | Read/write | no |
| C143 | Selects the drive action when embedded EtherNet/IP communications are disrupted. Non-fault selections can permit continued operation and require commissioning verification. | See option set: EtherNet/IP Fault Action | — | 0 | — | Read/write | no |
| C144 | Selects the drive action when the EtherNet/IP scanner becomes idle because the controller enters Program mode. Non-fault selections can permit continued operation and require commissioning verification. | See option set: EtherNet/IP Fault Action | — | 0 | — | Read/write | no |

Parameter option sets:

#### Analog Output Selection

| Value | Meaning |
| ---: | --- |
| 0 | Output Frequency 0–10 V |
| 1 | Output Current 0–10 V |
| 2 | Output Voltage 0–10 V |
| 3 | Output Power 0–10 V |
| 4 | Output Torque 0–10 V |
| 5 | Test Data 0–10 V |
| 6 | Setpoint 0–10 V |
| 7 | DC Bus Voltage 0–10 V |
| 8 | Output Frequency 0–20 mA |
| 9 | Output Current 0–20 mA |
| 10 | Output Voltage 0–20 mA |
| 11 | Output Power 0–20 mA |
| 12 | Output Torque 0–20 mA |
| 13 | Test Data 0–20 mA |
| 14 | Setpoint 0–20 mA |
| 15 | DC Bus Voltage 0–20 mA |
| 16 | Output Frequency 4–20 mA |
| 17 | Output Current 4–20 mA |
| 18 | Output Voltage 4–20 mA |
| 19 | Output Power 4–20 mA |
| 20 | Output Torque 4–20 mA |
| 21 | Test Data 4–20 mA |
| 22 | Setpoint 4–20 mA |
| 23 | DC Bus Voltage 4–20 mA |

#### EtherNet/IP Fault Action

| Value | Meaning |
| ---: | --- |
| 0 | Fault |
| 1 | Stop |
| 2 | Zero Data |
| 3 | Hold Last |
| 4 | Send Fault Configuration |

#### Programmable Digital Input

| Value | Meaning |
| ---: | --- |
| 0 | Not Used |
| 1 | Speed Ref 2 |
| 2 | Speed Ref 3 |
| 3 | Start Src 2 |
| 4 | Start Src 3 |
| 5 | Spd + Strt 2 |
| 6 | Spd + Strt 3 |
| 7 | Preset Freq |
| 8 | Jog |
| 9 | Jog Forward |
| 10 | Jog Reverse |
| 11 | Acc/Dec Sel2 |
| 12 | Aux Fault |
| 13 | Clear Fault |
| 14 | RampStop,CF |
| 15 | CoastStop,CF |
| 16 | DCInjStop,CF |
| 17 | MOP Up |
| 18 | MOP Down |
| 19 | Timer Start |
| 20 | Counter In |
| 21 | Reset Timer |
| 22 | Reset Counter |
| 23 | Reset Timer & Counter |
| 24 | Logic In 1 |
| 25 | Logic In 2 |
| 26 | Current Limit 2 |
| 27 | Analog Invert |
| 28 | EM Brake Release |
| 29 | Acc/Dec Sel3 |
| 30 | Precharge Enable |
| 31 | Inertia Decel |
| 32 | Sync Enable |
| 33 | Traverse Disable |
| 34 | Home Limit |
| 35 | Find Home |
| 36 | Hold Step |
| 37 | Position Redefine |
| 38 | Force DC |
| 39 | Damper Input |
| 40 | Purge |
| 41 | Freeze-Fire |
| 42 | Software Enable |
| 43 | Shear Pin 1 Disable |
| 44 | Reserved |
| 45 | Reserved |
| 46 | Reserved |
| 47 | Reserved |
| 48 | 2-Wire Forward |
| 49 | 3-Wire Start |
| 50 | 2-Wire Reverse |
| 51 | 3-Wire Direction |
| 52 | Pulse Train |

#### Programmable Digital Output

| Value | Meaning |
| ---: | --- |
| 0 | Ready/Fault |
| 1 | At Frequency |
| 2 | Motor Running |
| 3 | Reverse |
| 4 | Motor Overload |
| 5 | Ramp Regulator |
| 6 | Above Frequency |
| 7 | Above Current |
| 8 | Above DC Voltage |
| 9 | Retries Exhausted |
| 10 | Above Analog Voltage |
| 11 | Above Power Factor Angle |
| 12 | Analog Input Loss |
| 13 | Parameter Control |
| 14 | Non-Resettable Fault |
| 15 | EM Brake Control |
| 16 | Thermal Overload |
| 17 | Ambient Overtemperature |
| 18 | Local Active |
| 19 | Communication Loss |
| 20 | Logic Input 1 |
| 21 | Logic Input 2 |
| 22 | Logic 1 AND 2 |
| 23 | Logic 1 OR 2 |
| 24 | StepLogic Output |
| 25 | Timer Output |
| 26 | Counter Output |
| 27 | At Position |
| 28 | At Home |
| 29 | Safe-Off |
| 30 | Safe Torque Permit |
| 31 | Auto-Restart Countdown |

#### Speed Reference

| Value | Meaning |
| ---: | --- |
| 1 | Drive Potentiometer |
| 2 | Keypad Frequency |
| 3 | Serial/DSI |
| 4 | Network Option |
| 5 | 0–10 V Input |
| 6 | 4–20 mA Input |
| 7 | Preset Frequency |
| 8 | Analog Input Multiply |
| 9 | MOP |
| 10 | Pulse Input |
| 11 | PID1 Output |
| 12 | PID2 Output |
| 13 | Step Logic |
| 14 | Encoder |
| 15 | EtherNet/IP |
| 16 | Positioning |

#### Start Source

| Value | Meaning |
| ---: | --- |
| 1 | Keypad |
| 2 | Digital Input Terminal Block |
| 3 | Serial/DSI |
| 4 | Network Option |
| 5 | EtherNet/IP |

Evidence:

- Dev_PF525.Main: Dvc_PF525 instance Dvc parameter Ref_Module references Dev_PF525
- Dev_PF525.Main: Dvc_PF525 instance Dvc parameter Ref_DataIn references Dev_PF525:I
- Dev_PF525.Main: Dvc_PF525 instance Dvc parameter Ref_DataOut references Dev_PF525:O

## Diagnostics and unresolved evidence

No corpus diagnostics or unassigned documents.
