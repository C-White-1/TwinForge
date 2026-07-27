# Dvc_PF525 AOI QA verification register

## Purpose

This register records potential AOI quality issues discovered while comparing
`Dvc_PF525_AOI.L5X` with Rockwell Automation publication
520-UM001L-EN-E. Entries are verification candidates, not confirmed defects.
No AOI source has been changed.

## Status summary

| ID | Severity | Area | Status | Summary |
| --- | --- | --- | --- | --- |
| PF525-QA-001 | High | T105 default | Open | Described AOI default conflicts with embedded setpoint initialization |
| PF525-QA-002 | High | T105 safety semantics | Open | AOI description says either safety input; manual condition refers to both |
| PF525-QA-003 | Medium | C143 documentation | Open | Option 4 is accepted by logic but omitted from the member description |
| PF525-QA-004 | Medium | C144 documentation | Open | Option 4 is accepted by logic but omitted from the member description |
| PF525-QA-005 | Low | T105 documentation | Open | Description contains a spelling error |
| PF525-QA-006 | Low | T099 documentation | Open | Member description contains only the parameter code |
| PF525-QA-007 | Low | T088 documentation | Open | Description lists selected modes rather than the complete option range |
| PF525-QA-008 | Low | b008/b009 documentation | Open | Fault-history member descriptions contain only parameter codes |
| PF525-QA-009 | Medium | A440 exposure | Open | Read request exists, but its assignment is commented out and no AOI member exposes the value |
| PF525-QA-010 | Medium | A490 validation | Open | AOI permits twice the manual maximum load-loss threshold |
| PF525-QA-011 | High | A544 write safety | Open | AOI does not enforce the documented stop-only or option-range constraints |
| PF525-QA-012 | Medium | A545 validation | Open | AOI writes the flying-start option without validating its range |
| PF525-QA-013 | Medium | A546 default | Open | AOI initialization and write comment use 150%, while the manual and member description use 65% |
| PF525-QA-014 | Medium | A576 documentation | Open | AOI gives the wrong induction-motor default for phase-loss sensitivity |
| PF525-QA-015 | High | A572 write safety | Open | AOI forces a stop-only parameter without checking that the drive is inactive |
| PF525-QA-016 | Low | F604–F610 documentation | Open | Extended fault-history descriptions contain only parameter codes |
| PF525-QA-017 | Low | F631–F640 terminology | Open | AOI calls output-frequency snapshots “Speed” |
| PF525-QA-018 | Low | F641–F650 documentation | Open | Fault-current descriptions contain only parameter codes |
| PF525-QA-019 | Low | F651–F660 documentation | Open | Fault DC-bus-voltage descriptions contain only parameter codes |

## Findings

### PF525-QA-001 — T105 described default conflicts with initialization

- Severity: High
- Status: Open
- AOI member: `Local.Params.SafetyOpenFaultDisable`
- AOI description: option 0 is identified as the drive default and option 1
  as “our default.”
- Embedded initialization: both `PV` and `SP` are initialized to `0`.
- Manual evidence: T105 factory default is option 0, Fault Enable.
- Potential impact: a user may expect the AOI to request Fault Disable while
  the initial setpoint actually requests or retains Fault Enable.
- Manual verification:
  1. Instantiate the AOI with no external write to
     `Cfg_SafetyOpenFaultDisable`.
  2. Confirm the initial value of
     `Local.Params.SafetyOpenFaultDisable.SP`.
  3. Confirm whether another initialization path changes the setpoint to 1.
  4. Decide whether the description or initialization should be corrected.

### PF525-QA-002 — T105 safety-input condition differs from the manual

- Severity: High
- Status: Open
- AOI description: describes the condition as either safety input being
  de-energized.
- Manual evidence: T105 is described for both Safety 1 and Safety 2 being
  de-energized.
- Potential impact: the AOI documentation may give an incorrect expectation
  of the drive fault response for a single open safety channel.
- Manual verification:
  1. Confirm the intended PowerFlex 525 firmware revision.
  2. Test Safety 1 open, Safety 2 open, and both channels open separately.
  3. Record the resulting drive state and fault indication for T105 values 0
     and 1.
  4. Correct the AOI description if the manual behaviour is confirmed.

### PF525-QA-003 — C143 option 4 omitted from the description

- Severity: Medium
- Status: Open
- AOI member: `Local.Params.ENetCommFaultAction`
- AOI description: lists values 0 through 3.
- AOI validation logic: accepts values from 0 through 4.
- Manual evidence: value 4 is Send Fault Configuration.
- Potential impact: users may not know that the AOI supports the configured
  fault-action data in C145 through C150.
- Manual verification: confirm option 4 operation on the target firmware and
  add it to the AOI member description.

### PF525-QA-004 — C144 option 4 omitted from the description

- Severity: Medium
- Status: Open
- AOI member: `Local.Params.ENetCommIdleAction`
- AOI description: lists values 0 through 3.
- AOI validation logic: accepts values from 0 through 4.
- Manual evidence: value 4 is Send Fault Configuration.
- Potential impact: users may not know that the AOI supports configured data
  when the EtherNet/IP scanner becomes idle.
- Manual verification: confirm option 4 operation on the target firmware and
  add it to the AOI member description.

### PF525-QA-005 — T105 spelling error

- Severity: Low
- Status: Open
- AOI text uses `de-energied`.
- Suggested correction: `de-energized`.

### PF525-QA-006 — T099 description is incomplete

- Severity: Low
- Status: Open
- AOI description contains only `T099`.
- Manual evidence: T099 controls additional analog-input filtering, accepts
  values 0 through 14, and each increment doubles the applied filtering.
- Potential impact: users cannot determine the parameter purpose or range
  from the AOI member.
- Manual verification: confirm the supported firmware range and enrich the
  member description.

### PF525-QA-007 — T088 description lists only selected modes

- Severity: Low
- Status: Open
- AOI description names options 0, 6, 14, and 22.
- Manual evidence: T088 accepts options 0 through 23.
- Potential impact: the text may be interpreted as a complete option list
  even though the AOI validation should be checked for all supported modes.
- Manual verification: determine whether the description intentionally
  highlights setpoint modes or should document the full supported range.

### PF525-QA-008 — b008 and b009 descriptions are incomplete

- Severity: Low
- Status: Open
- AOI descriptions contain only `B008` and `B009`.
- Manual evidence: b008 and b009 contain the second and third entries in the
  unique recent-fault history; b007 is the most recent entry.
- Potential impact: users cannot determine the ordering or duplicate-fault
  behaviour from these AOI members.
- Manual verification: confirm the history ordering on the target firmware
  and enrich both member descriptions.

### PF525-QA-009 — A440 read value is discarded

- Severity: Medium
- Status: Open
- Read-message setup: assigns parameter 440 to `Ref_MsgData[20]`.
- Read-message result handling: the assignment
  `Local.PWMFrequency := Ref_MsgData[20] * 0.1` is commented out.
- AOI interface: no `PWMFrequency` member or alias exposes either the process
  value or a setpoint.
- Manual evidence: A440 sets PWM carrier frequency from 2.0 through 16.0 kHz
  with 0.1 kHz resolution and is not read-only.
- Potential impact: the AOI requests A440 on every applicable read cycle but
  discards the result, while users cannot monitor or configure the parameter
  through the AOI interface.
- Manual verification:
  1. Confirm whether A440 was intentionally removed from the AOI interface.
  2. Confirm that read slot 20 returns A440 on the target firmware.
  3. If support is intended, restore a typed parameter member and the scaled
     result assignment, then add the corresponding write-message mapping.
  4. If support is not intended, remove the unused read request.

### PF525-QA-010 — A490 validation exceeds the documented maximum

- Severity: Medium
- Status: Open
- AOI member description: identifies the maximum as drive-rated current.
- AOI write validation: accepts `LoadLossLevel.SP` through
  `RatedCurrent * 2.0`.
- Manual evidence: A490 has a maximum of drive-rated current.
- Potential impact: the AOI can issue a setpoint above the documented drive
  range. It is unclear whether the drive rejects, clips, or accepts such a
  write, and a high threshold could undermine the intended load-loss
  protection.
- Manual verification:
  1. Confirm the applicable drive firmware and its accepted A490 range.
  2. Test a write between one and two times drive-rated current in a safe,
     controlled environment.
  3. Record whether the drive rejects or clips the value and how the AOI
     reports the result.
  4. If the manual limit is confirmed, change the AOI validation maximum to
     `RatedCurrent`.

### PF525-QA-011 — A544 write omits stop and range checks

- Severity: High
- Status: Open
- Manual evidence: A544 must be changed while the drive is stopped and accepts
  only 0, Reverse Enabled, or 1, Reverse Disabled.
- AOI write logic: writes any changed setpoint without checking
  `NOT Sts_Active` or restricting the value to 0 or 1.
- Potential impact: the AOI may attempt a direction-permission change while
  the drive is active or issue an undocumented option value. Whether the drive
  rejects either request depends on device and firmware behaviour.
- Manual verification:
  1. Confirm the accepted A544 values on the applicable firmware.
  2. Verify that an active drive rejects an A544 write without changing
     direction behaviour.
  3. Add both an inactive-state interlock and a 0-through-1 range check to the
     AOI write path.

### PF525-QA-012 — A545 write omits option validation

- Severity: Medium
- Status: Open
- Manual and AOI descriptions: A545 accepts only 0, Disabled, and 1, Enabled.
- AOI write logic: writes any changed setpoint without checking the value.
- Potential impact: an out-of-range setpoint can be sent to the drive, leaving
  rejection and recovery behaviour dependent on firmware.
- Manual verification: test an invalid value safely, record the device
  response, and add a 0-through-1 validation check with setpoint rollback.

### PF525-QA-013 — A546 default conflicts with the manual

- Severity: Medium
- Status: Open
- Manual evidence: A546 factory default is 65%.
- AOI member description: identifies 65% as the default.
- AOI initialization: sets `FlyingStartCurrentLimit.SP` to 150%.
- AOI write-routine comment: also identifies 150% as the default.
- Potential impact: after initialization, the AOI can request a substantially
  higher flying-start current limit than the documented factory default.
- Manual verification:
  1. Confirm whether 150% is a deliberate library application default.
  2. Record the engineering basis and motor/drive limitations if deliberate.
  3. Otherwise initialize the setpoint to 65% and correct the write comment.

### PF525-QA-014 — A576 induction-motor default is incorrect

- Severity: Medium
- Status: Open
- AOI member description: identifies the A576 defaults as 0% for induction
  motors and 4% for permanent-magnet motors.
- Manual evidence: the defaults are 25% for induction motors and 4% for
  permanent-magnet motors.
- Potential impact: an engineer relying on the AOI description may select a
  phase-loss threshold with materially lower sensitivity than intended.
- Manual verification: confirm the defaults on each supported firmware and
  correct the AOI member description from 0% to 25% for induction motors.

### PF525-QA-015 — A572 automatic write omits the stop interlock

- Severity: High
- Status: Open
- Manual evidence: the drive must be stopped before changing A572.
- AOI policy: A572 is intentionally maintained at 1.00.
- AOI write logic: whenever its process value differs from 1.00, the AOI
  writes 100 raw counts without checking `NOT Sts_Active`.
- Potential impact: an AOI invocation can attempt to change a stop-only speed
  scaling parameter while the drive is active. Device rejection behaviour is
  firmware-dependent; acceptance could cause an immediate speed-reference
  scaling change.
- Manual verification:
  1. Confirm the intended reason for forcing A572 to 1.00.
  2. Test active-drive rejection safely on each supported firmware.
  3. Add an inactive-state interlock before issuing the automatic write.
  4. Consider reporting a configuration mismatch while active rather than
     repeatedly requesting the write.

### PF525-QA-016 — F604 through F610 descriptions are incomplete

- Severity: Low
- Status: Open
- AOI descriptions: contain only the respective parameter codes.
- Manual evidence: F604 through F610 are entries 4 through 10 in the unique
  recent-fault history; b007 is the most recent entry and repeated faults are
  recorded only once.
- Potential impact: users cannot determine the history ordering or duplicate
  handling from the AOI member descriptions.
- Manual verification: confirm ordering on the target firmware and enrich the
  seven member descriptions with their history positions.

### PF525-QA-017 — F631 through F640 are named as speed, not frequency

- Severity: Low
- Status: Open
- AOI evidence: members are named `Fault01Speed` through `Fault10Speed`, and
  their descriptions contain only the respective parameter codes.
- Manual evidence: F631 through F640 are `[Fault 1 Freq]` through
  `[Fault10 Freq]`. Each stores b001 `[Output Freq]` for the corresponding
  recent fault, in hertz with 0.01 Hz display resolution.
- Potential impact: consumers could interpret the values as shaft speed in
  RPM rather than electrical output frequency in hertz.
- Manual verification: confirm values against the drive display and consider
  frequency-based member names or enriched descriptions in a future AOI
  revision.

### PF525-QA-018 — F641 through F650 descriptions are incomplete

- Severity: Low
- Status: Open
- AOI evidence: the `Fault01Current` through `Fault10Current` descriptions
  contain only the respective parameter codes.
- Manual evidence: F641 through F650 store b003 `[Output Current]` with each
  of the ten most recent faults. Values are in amperes, from zero through
  twice the drive-rated current, with 0.01 A display resolution.
- Potential impact: consumers cannot determine the unit, range, or
  fault-history ordering from the AOI member descriptions.
- Manual verification: compare the captured current against the drive fault
  history and enrich the AOI descriptions in a future revision.

### PF525-QA-019 — F651 through F660 descriptions are incomplete

- Severity: Low
- Status: Open
- AOI evidence: the `Fault01BusVoltage` through `Fault10BusVoltage`
  descriptions contain only the respective parameter codes.
- Manual evidence: F651 through F660 store b005 `[DC Bus Voltage]` with each
  of the ten most recent faults. Values range from 0 through 1200 V DC with
  1 V DC display resolution.
- Potential impact: consumers cannot determine the electrical quantity,
  unit, range, or fault-history ordering from the member descriptions.
- Manual verification: compare the captured voltage against the drive fault
  history and enrich the AOI descriptions in a future revision.

## Review notes

- Safety-related findings require validation by qualified personnel using the
  applicable drive firmware, risk assessment, and site safety procedures.
- Communication fault and idle actions must be commissioned deliberately;
  non-fault actions can permit continued drive operation.
- Update each status to `Confirmed`, `Rejected`, or `Resolved` only after
  recording test evidence.
