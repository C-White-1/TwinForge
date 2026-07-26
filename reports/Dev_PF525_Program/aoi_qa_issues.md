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

## Review notes

- Safety-related findings require validation by qualified personnel using the
  applicable drive firmware, risk assessment, and site safety procedures.
- Communication fault and idle actions must be commissioned deliberately;
  non-fault actions can permit continued drive operation.
- Update each status to `Confirmed`, `Rejected`, or `Resolved` only after
  recording test evidence.
