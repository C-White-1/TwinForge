# Dvc parameter and setpoint report

Configured values are shown only when recoverable from offline source evidence. Runtime values require a separate online or captured-data source.

- Configured-value evidence: 60/163 parameters
- Runtime-value evidence: 0/163 parameters
- Interpreted configured values: 30/60
- Mechanically verified configured values: 52/60
- Configuration assessment exceptions: 0
- Parameters with QA advisories: 51
- Parameters with high-severity advisories: 3

| Code | Name | Group | Configured value | Meaning | Assessment | Configuration note | Runtime value | Units | Range | Default | Access | Stop required | QA advisories |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | :---: | --- |
| b001 | Output Freq | Basic Display | — | — | — | — | — | Hz | 0.00 to P044 Maximum Freq | — | read | no | — |
| b002 | Commanded Freq | Basic Display | — | — | — | — | — | Hz | 0.00 to P044 Maximum Freq | — | read | no | — |
| b003 | Output Current | Basic Display | — | — | — | — | — | A | 0.00 to Drive Rated Amps × 2 | — | read | no | — |
| b004 | Output Voltage | Basic Display | — | — | — | — | — | V | 0.0 to Drive Rated Volts | — | read | no | — |
| b005 | DC Bus Voltage | Basic Display | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | — |
| b006 | Drive Status | Basic Display | — | — | — | — | — | — | 00000 to 11111 | — | read | no | — |
| b007 | Fault 1 Code | Basic Display | — | — | — | — | — | — | F0 to F127 | — | read | no | — |
| b008 | Fault 2 Code | Basic Display | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-008 |
| b009 | Fault 3 Code | Basic Display | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-008 |
| b012 | Control Source | Basic Display | — | — | — | — | — | — | 0000 to 2165 | — | read | no | — |
| b013 | Control Input Status | Basic Display | — | — | — | — | — | — | 0000 to 1111 | — | read | no | — |
| b014 | Digital Input Status | Basic Display | — | — | — | — | — | — | 0000 to 1111 | — | read | no | — |
| b015 | Output RPM | Basic Display | — | — | — | — | — | rpm | 0 to 24000 | — | read | no | — |
| b016 | Output Speed | Basic Display | — | — | — | — | — | % | 0.0 to 100.0 | — | read | no | — |
| b017 | Output Power | Basic Display | — | — | — | — | — | kW | 0.00 to Drive Rated Power × 2 | — | read | no | — |
| b019 | Elapsed Run Time | Basic Display | — | — | — | — | — | h | 0 to 65535 × 10 | — | read | no | — |
| b020 | Average Power | Basic Display | — | — | — | — | — | kW | 0.00 to Drive Rated Power × 2 | — | read | no | — |
| b021 | Elapsed kWh | Basic Display | — | — | — | — | — | kWh | 0.0 to 100.0 | — | read | no | — |
| b022 | Elapsed MWh | Basic Display | — | — | — | — | — | MWh | 0.0 to 6553.5 | — | read | no | — |
| b027 | Drive Temp | Basic Display | — | — | — | — | — | °C | 0 to 120 | — | read | no | — |
| b028 | Control Temp | Basic Display | — | — | — | — | — | °C | 0 to 120 | — | read | no | — |
| b029 | Control SW Version | Basic Display | — | — | — | — | — | — | 0.000 to 65.535 | — | read | no | — |
| P031 | Motor NP Volts | Basic Program | 230 | — | Not automatically verifiable | — | — | V | 10 (230 V drives), 20 (460 V drives), or 25 (600 V drives) to Drive Rated Volts | Drive Rated Volts | read/write | yes | — |
| P032 | Motor NP Hertz | Basic Program | 60 | — | Within documented range | — | — | Hz | 15 to 500 | 60 | read/write | yes | — |
| P033 | Motor OL Current | Basic Program | 2.5 | — | Not automatically verifiable | — | — | A | 0.0 to Drive Rated Amps × 2 | Drive Rated Amps | read/write | no | — |
| P034 | Motor NP FLA | Basic Program | 2.5 | — | Not automatically verifiable | — | — | A | 0.1 to Drive Rated Amps × 2 | Based on Drive Rating | read/write | no | — |
| P035 | Motor NP Poles | Basic Program | 4 | — | Within documented range | — | — | — | 2 to 40 | 4 | read/write | no | — |
| P036 | Motor NP RPM | Basic Program | 1750 | — | Within documented range | — | — | rpm | 0 to 24000 | 1750 | read/write | yes | — |
| P037 | Motor NP Power | Basic Program | 0.37 | — | Not automatically verifiable | — | — | kW | 0.00 to Drive Rated Power | Drive Rated Power | read/write | no | — |
| P038 | Voltage Class | Basic Program | 3 | High Voltage (600 V) | Documented option | — | — | — | — | 3 | read/write | yes | — |
| P039 | Torque Perf Mode | Basic Program | 1 | SVC | Documented option | — | — | — | — | 1 | read/write | yes | — |
| P040 | Autotune | Basic Program | — | — | — | — | — | — | — | 0 | read | yes | — |
| P041 | Accel Time 1 | Basic Program | 10.0 | — | Within documented range | — | — | s | 0.00 to 600.00 | 10.00 | read/write | no | — |
| P042 | Decel Time 1 | Basic Program | 10.0 | — | Within documented range | — | — | s | 0.00 to 600.00 | 10.00 | read/write | no | — |
| P043 | Minimum Freq | Basic Program | 0.0 | — | Within documented range | — | — | Hz | 0.00 to 500.00 | 0.00 | read/write | yes | — |
| P044 | Maximum Freq | Basic Program | 60.0 | — | Within documented range | — | — | Hz | 0.00 to 500.00 | 60.00 | read/write | yes | — |
| P045 | Stop Mode | Basic Program | 0 | Ramp, CF | Documented option | — | — | — | — | 0 | read/write | no | — |
| P046 | Start Source 1 | Basic Program | 5 | EtherNet/IP | Documented option | — | — | — | — | 1 | read/write | yes | — |
| P047 | Speed Reference 1 | Basic Program | 15 | EtherNet/IP | Documented option | — | — | — | — | 1 | read/write | no | — |
| P048 | Start Source 2 | Basic Program | 2 | Digital Input Terminal Block | Documented option | — | — | — | — | 2 | read/write | yes | — |
| P049 | Speed Reference 2 | Basic Program | 5 | 0–10 V Input | Documented option | — | — | — | — | 5 | read/write | no | — |
| P050 | Start Source 3 | Basic Program | 5 | EtherNet/IP | Documented option | — | — | — | — | 5 | read/write | yes | — |
| P051 | Speed Reference 3 | Basic Program | 15 | EtherNet/IP | Documented option | — | — | — | — | 15 | read/write | no | — |
| P053 | Reset To Defaults | Basic Program | — | — | — | AOI writes internal setpoint Local.Params.ResetToDefaults.SP, but no unique exported instance value was found. | — | — | — | 0 | read/write | yes | — |
| T062 | DigIn TermBlk 02 | Terminal Block | 0 | Not Used | Documented option | — | — | — | — | 48 | read/write | yes | — |
| T063 | DigIn TermBlk 03 | Terminal Block | 0 | Not Used | Documented option | — | — | — | — | 50 | read/write | yes | — |
| T064 | 2-Wire Mode | Terminal Block | 0 | Edge Trigger | Documented option | — | — | — | — | 0 | read/write | yes | — |
| T065 | DigIn TermBlk 05 | Terminal Block | 0 | Not Used | Documented option | — | — | — | — | 7 | read/write | yes | — |
| T066 | DigIn TermBlk 06 | Terminal Block | 0 | Not Used | Documented option | — | — | — | — | 7 | read/write | yes | — |
| T067 | DigIn TermBlk 07 | Terminal Block | 0 | Not Used | Documented option | — | — | — | — | 5 | read/write | yes | — |
| T068 | DigIn TermBlk 08 | Terminal Block | 9 | Jog Forward | Documented option | — | — | — | — | 9 | read/write | yes | — |
| T069 | Opto Out1 Sel | Terminal Block | 13 | Parameter Control | Documented option | — | — | — | — | 2 | read/write | no | — |
| T070 | Opto Out1 Level | Terminal Block | — | — | — | AOI writes internal setpoint Local.Params.Opto1Level.SP, but no unique exported instance value was found. | — | — | 0.0 to 9999.0 | 0.0 | read/write | no | — |
| T072 | Opto Out2 Sel | Terminal Block | 13 | Parameter Control | Documented option | — | — | — | — | 1 | read/write | no | — |
| T073 | Opto Out2 Level | Terminal Block | — | — | — | AOI writes internal setpoint Local.Params.Opto2Level.SP, but no unique exported instance value was found. | — | — | 0.0 to 9999.0 | 0.0 | read/write | no | — |
| T075 | Opto Out Logic | Terminal Block | 0 | Output 1 NO; Output 2 NO | Documented option | — | — | — | — | 0 | read/write | no | — |
| T076 | Relay Out1 Sel | Terminal Block | 13 | Parameter Control | Documented option | — | — | — | — | 0 | read/write | no | — |
| T077 | Relay Out1 Level | Terminal Block | — | — | — | AOI writes internal setpoint Local.Params.Relay1Level.SP, but no unique exported instance value was found. | — | — | 0.0 to 9999.0 | 0.0 | read/write | no | — |
| T079 | Relay 1 On Time | Terminal Block | 0.0 | — | Within documented range | — | — | s | 0.0 to 600.0 | 0.0 | read/write | no | — |
| T080 | Relay 1 Off Time | Terminal Block | 0.0 | — | Within documented range | — | — | s | 0.0 to 600.0 | 0.0 | read/write | no | — |
| T081 | Relay Out2 Sel | Terminal Block | 13 | Parameter Control | Documented option | — | — | — | — | 2 | read/write | no | — |
| T082 | Relay Out2 Level | Terminal Block | — | — | — | AOI writes internal setpoint Local.Params.Relay2Level.SP, but no unique exported instance value was found. | — | — | 0.0 to 9999.0 | 0.0 | read/write | no | — |
| T084 | Relay 2 On Time | Terminal Block | 0.0 | — | Within documented range | — | — | s | 0.0 to 600.0 | 0.0 | read/write | no | — |
| T085 | Relay 2 Off Time | Terminal Block | 0.0 | — | Within documented range | — | — | s | 0.0 to 600.0 | 0.0 | read/write | no | — |
| T088 | Analog Out Sel | Terminal Block | 0 | Output Frequency 0–10 V | Documented option | — | — | — | — | 0 | read/write | no | Low: PF525-QA-007 |
| T090 | Analog Out Setpoint | Terminal Block | 0.0 | — | Within documented range | — | — | % | 0.0 to 100.0 | 0.0 | read/write | no | — |
| T099 | Analog In Filter | Terminal Block | 0 | — | Within documented range | — | — | — | 0 to 14 | 0 | read/write | no | Low: PF525-QA-006 |
| T105 | Safety Open Enable | Terminal Block | 1 | Fault Disable | Documented option | — | — | — | — | 0 | read/write | no | High: PF525-QA-001, PF525-QA-002, PF525-QA-005 |
| T106 | Safety Fault Reset Configuration | Terminal Block | 0 | Power-Cycle Reset | Documented option | — | — | — | — | 0 | read/write | no | — |
| C143 | EN Comm Flt Actn | Communications | 0 | Fault | Documented option | — | — | — | — | 0 | read/write | no | Medium: PF525-QA-003 |
| C144 | EN Idle Flt Actn | Communications | 0 | Fault | Documented option | — | — | — | — | 0 | read/write | no | Medium: PF525-QA-004 |
| d360 | Analog In 0-10V | Advanced Display | — | — | — | — | — | % | 0.0 to 100.0 | — | read | no | — |
| d361 | Analog In 4-20mA | Advanced Display | — | — | — | — | — | % | 0.0 to 100.0 | — | read | no | — |
| d362 | Elapsed Time-hr | Advanced Display | — | — | — | — | — | h | 0 to 32767 | — | read | no | — |
| d363 | Elapsed Time-min | Advanced Display | — | — | — | — | — | min | 0.0 to 60.0 | — | read | no | — |
| d364 | Counter Status | Advanced Display | — | — | — | — | — | — | 0 to 65535 | — | read | no | — |
| d367 | Drive Type | Advanced Display | — | — | — | — | — | — | 0 to 65535 | — | read | no | — |
| d369 | Motor OL Level | Advanced Display | — | — | — | — | — | % | 0.0 to 150.0 | — | read | no | — |
| d375 | Slip Hz Meter | Advanced Display | — | — | — | — | — | Hz | 0.0 to 25.0 | — | read | no | — |
| d376 | Speed Feedback | Advanced Display | — | — | — | — | — | rpm | 0.0 to 64000.0 | — | read | no | — |
| d378 | Encoder Speed | Advanced Display | — | — | — | — | — | rpm | 0.0 to 64000.0 | — | read | no | — |
| d380 | DC Bus Ripple | Advanced Display | — | — | — | — | — | V DC | 0 to 410 (230 V AC drive), 820 (460 V AC drive), or 1025 (600 V AC drive) | — | read | no | — |
| d381 | Output Powr Fctr | Advanced Display | — | — | — | — | — | ° | 0.0 to 180.0 | — | read | no | — |
| d382 | Torque Current | Advanced Display | — | — | — | — | — | A | 0.00 to Drive Rated Amps × 2 | — | read | no | — |
| d393 | Drive Status 2 | Advanced Display | — | — | — | — | — | — | 0 to 65535 | — | read | no | — |
| d394 | Dig Out Status | Advanced Display | — | — | — | — | — | — | 0 to 15 | — | read | no | — |
| A431 | Jog Frequency | Advanced Program | 10.0 | — | Not automatically verifiable | — | — | Hz | 0.00 to P044 Maximum Freq | 10.00 | read/write | yes | — |
| A432 | Jog Accel/Decel | Advanced Program | 10.0 | — | Within documented range | — | — | s | 0.01 to 600.00 | 10.00 | read/write | yes | — |
| A434 | DC Brake Time | Advanced Program | — | — | — | AOI writes internal setpoint Local.Params.DCBrakeTime.SP, but no unique exported instance value was found. | — | s | 0.0 to 99.9 | 0.0 | read/write | yes | — |
| A435 | DC Brake Level | Advanced Program | 0.12 | — | Not automatically verifiable | — | — | A | 0.00 to Drive Rated Amps × 1.80 | Drive Rated Amps × 0.05 | read/write | yes | — |
| A439 | S Curve % | Advanced Program | 0 | — | Within documented range | — | — | % | 0 to 100 | 0 | read/write | yes | — |
| A440 | PWM Frequency | Advanced Program | — | — | — | — | — | kHz | 2.0 to 16.0 | 4.0 | read | no | Medium: PF525-QA-009 |
| A441 | Droop Hertz@ FLA | Advanced Program | 0.0 | — | Within documented range | — | — | Hz | 0.0 to 10.0 | 0.0 | read/write | yes | — |
| A486 | Shear Pin1 Level | Advanced Program | 0.0 | — | Not automatically verifiable | — | — | A | 0.0 to Drive Rated Amps × 2 | 0.0 | read/write | yes | — |
| A487 | Shear Pin 1 Time | Advanced Program | 0.0 | — | Within documented range | — | — | s | 0.00 to 30.00 | 0.00 | read/write | yes | — |
| A490 | Load Loss Level | Advanced Program | 0.0 | — | Not automatically verifiable | — | — | A | 0.0 to Drive Rated Amps | 0.0 | read/write | yes | Medium: PF525-QA-010 |
| A491 | Load Loss Time | Advanced Program | 0 | — | Within documented range | — | — | s | 0 to 9999 | 0 | read/write | yes | — |
| A534 | Maximum Voltage | Advanced Program | — | — | — | AOI writes internal setpoint Local.Params.MaximumVoltage.SP, but no unique exported instance value was found. | — | V AC | 10 (230 V drive), 20 (460 V drive), or 25 (600 V drive) to 255 (230 V drive), 510 (460 V drive), or 637.5 (600 V drive) | Drive Rated Volts | read/write | yes | — |
| A535 | Motor Fdbk Type | Advanced Program | 0 | None | Documented option | — | — | — | — | 0 | read/write | yes | — |
| A536 | Encoder PPR | Advanced Program | 1024 | — | Within documented range | — | — | PPR | 1 to 20000 | 1024 | read/write | no | — |
| A537 | Pulse In Scale | Advanced Program | 64 | — | Within documented range | — | — | — | 0 to 20000 | 64 | read/write | no | — |
| A543 | Start At PowerUp | Advanced Program | — | — | — | AOI automatically writes raw literal 0; this is behavior, not saved configuration. | — | — | — | 0 | read/write | yes | — |
| A544 | Reverse Disable | Advanced Program | 0 | Reverse Enabled | Documented option | — | — | — | — | 0 | read/write | yes | High: PF525-QA-011 |
| A545 | Flying Start En | Advanced Program | 0 | Disabled | Documented option | — | — | — | — | 0 | read/write | no | Medium: PF525-QA-012 |
| A546 | FlyStrt CurLimit | Advanced Program | 150 | — | Within documented range | — | — | % | 30 to 200 | 65 | read/write | no | Medium: PF525-QA-013 |
| A547 | Compensation | Advanced Program | — | — | — | — | — | — | — | 1 | read | no | — |
| A548 | Power Loss Mode | Advanced Program | 0 | Coast | Documented option | — | — | — | — | 0 | read/write | no | — |
| A550 | Bus Reg Enable | Advanced Program | — | — | — | — | — | — | — | 1 | read | no | — |
| A551 | Fault Clear | Advanced Program | — | — | — | AOI automatically writes raw literal 2; this is behavior, not saved configuration. | — | — | — | 0 | read/write | yes | — |
| A555 | Reset Meters | Advanced Program | — | — | — | — | — | — | — | 0 | read | no | — |
| A559 | Counts Per Unit | Advanced Program | 4096 | — | Within documented range | — | — | — | 1 to 32000 | 4096 | read/write | no | — |
| A572 | Speed Ratio | Advanced Program | — | — | — | AOI automatically writes raw literal 100; this is behavior, not saved configuration. | — | — | 0.01 to 99.99 | 1.00 | read/write | yes | High: PF525-QA-015 |
| A575 | Flux Braking En | Advanced Program | — | — | — | — | — | — | — | 0 | read | no | — |
| A576 | Phase Loss Level | Advanced Program | — | — | — | — | — | % | 0.0 to 100.0 | 25.0 (induction motor) or 4.0 (PM motor) | read | no | Medium: PF525-QA-014 |
| F604 | Fault 4 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F605 | Fault 5 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F606 | Fault 6 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F607 | Fault 7 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F608 | Fault 8 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F609 | Fault 9 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F610 | Fault 10 Code | Fault and Diagnostic | — | — | — | — | — | — | F0 to F127 | — | read | no | Low: PF525-QA-016 |
| F631 | Fault 1 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F632 | Fault 2 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F633 | Fault 3 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F634 | Fault 4 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F635 | Fault 5 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F636 | Fault 6 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F637 | Fault 7 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F638 | Fault 8 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F639 | Fault 9 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F640 | Fault 10 Frequency | Fault and Diagnostic | — | — | — | — | — | Hz | 0.00 to 500.00 | — | read | no | Low: PF525-QA-017 |
| F641 | Fault 1 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F642 | Fault 2 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F643 | Fault 3 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F644 | Fault 4 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F645 | Fault 5 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F646 | Fault 6 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F647 | Fault 7 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F648 | Fault 8 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F649 | Fault 9 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F650 | Fault 10 Current | Fault and Diagnostic | — | — | — | — | — | A | 0.00 to Drive Rated Amps x 2 | — | read | no | Low: PF525-QA-018 |
| F651 | Fault 1 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F652 | Fault 2 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F653 | Fault 3 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F654 | Fault 4 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F655 | Fault 5 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F656 | Fault 6 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F657 | Fault 7 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F658 | Fault 8 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F659 | Fault 9 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F660 | Fault 10 DC Bus Voltage | Fault and Diagnostic | — | — | — | — | — | V DC | 0 to 1200 | — | read | no | Low: PF525-QA-019 |
| F693 | Active IP Address Octet 1 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F694 | Active IP Address Octet 2 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F695 | Active IP Address Octet 3 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F696 | Active IP Address Octet 4 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F697 | Active Subnet Mask Octet 1 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F698 | Active Subnet Mask Octet 2 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F699 | Active Subnet Mask Octet 3 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F700 | Active Subnet Mask Octet 4 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F701 | Active Gateway Address Octet 1 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F702 | Active Gateway Address Octet 2 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F703 | Active Gateway Address Octet 3 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |
| F704 | Active Gateway Address Octet 4 | Fault and Diagnostic | — | — | — | — | — | — | 0 to 255 | — | read | no | — |

## Review priorities

These are evidence-backed manual-review findings, not confirmed runtime defects.

### High

- `T105` Safety Open Enable; configured `1` (Fault Disable): PF525-QA-001, PF525-QA-002, PF525-QA-005 — AOI described default conflicts with initialization; AOI safety-input semantics differ from the manual; AOI description contains a spelling error.
- `A544` Reverse Disable; configured `0` (Reverse Enabled): PF525-QA-011 — AOI write omits stop and range checks.
- `A572` Speed Ratio: PF525-QA-015 — AOI forces a stop-only parameter without an inactive-state check.

### Medium

- `C143` EN Comm Flt Actn; configured `0` (Fault): PF525-QA-003 — AOI description omits accepted option 4.
- `C144` EN Idle Flt Actn; configured `0` (Fault): PF525-QA-004 — AOI description omits accepted option 4.
- `A440` PWM Frequency: PF525-QA-009 — AOI reads this value but does not expose it.
- `A490` Load Loss Level; configured `0.0`: PF525-QA-010 — AOI validation exceeds the documented maximum.
- `A545` Flying Start En; configured `0` (Disabled): PF525-QA-012 — AOI write omits option validation.
- `A546` FlyStrt CurLimit; configured `150`: PF525-QA-013 — AOI initialization conflicts with the documented default.
- `A576` Phase Loss Level: PF525-QA-014 — AOI gives the wrong induction-motor default.
