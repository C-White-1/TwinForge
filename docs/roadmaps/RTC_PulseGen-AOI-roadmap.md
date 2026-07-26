# RTC_PulseGen AOI conversion roadmap

This roadmap tracks conversion of the Rockwell `RTC_PulseGen` Add-On
Instruction without introducing an instruction-name special case. It is the
first evidence-backed use case for TwinForge's general AOI-to-IEC Structured
Text transformation and target-runtime adapter architecture.

## Objective

Convert the captured AOI into a stateful IEC function block that preserves:

- level-controlled enable behaviour;
- rising-enable initialization;
- configurable millisecond pulse interval;
- a one-controller-scan output pulse;
- initialization corresponding to the Rockwell prescan routine;
- clock failures without silently presenting stale data as valid.

The implementation must keep the neutral transformation independent of
CODESYS. CODESYS system libraries belong in its target adapter, with a future
OpenPLC adapter free to provide the same neutral clock capability differently.

## Verified source and target evidence

- [x] Capture AOI parameters, local tags, ST logic and prescan routine
- [x] Identify `GSV(WallClockTime, ..., CurrentValue, ...)`
- [x] Confirm Rockwell wall-clock values and interval arithmetic use
  microseconds
- [x] Introduce the neutral `wall_clock_read` runtime capability
- [x] Distinguish wall-clock `GSV` from module-object `GSV`
- [x] Export native CODESYS `08_rtc_high_res.xml`
- [x] Confirm `SysTimeRtcHighResGet` returns UTC milliseconds
- [x] Export native CODESYS `09_rtc_pulse.xml`
- [x] Confirm CODESYS function-block interfaces, instance state, ST calls and
  library metadata

The native XML files are implementation evidence in the ignored
`reference/PLCopenXML/codesys-native/` directory. Their relevant findings are
recorded in `docs/standards/plcopen.md`.

## Phase 1: general Structured Text transformation

- [ ] Parse supported ST statements into a lossless intermediate
  representation while retaining the original text
- [ ] Represent assignments, conditionals, Boolean expressions, arithmetic,
  member access and instruction calls
- [ ] Preserve unsupported expressions with diagnostics rather than
  discarding them
- [ ] Add datatype and numeric-unit transformation rules
- [ ] Resolve AOI parameter, local-tag and nested-AOI references
- [ ] Emit target-neutral IEC Structured Text

Completion criterion: `RTC_PulseGen` logic can be transformed without checking
for the name `RTC_PulseGen`.

## Phase 2: lifecycle and state mapping

- [ ] Map AOI local tags to IEC function-block instance variables
- [ ] Map input and output parameters with explicit direction and datatype
- [ ] Translate prescan initialization to defined target startup semantics
- [ ] Verify cold-start, warm-start and re-enable behaviour
- [ ] Preserve the one-scan pulse width under different task periods
- [ ] Diagnose unsupported postscan or enable-in-false behaviour

Completion criterion: executable tests demonstrate the same observable pulse
sequence for equivalent clock samples and enable transitions.

## Phase 3: target adapters

### CODESYS

- [ ] Implement `wall_clock_read` using `SysTimeRtcHighResGet`
- [ ] Emit `SysTime`, `SysTypes.RTS_IEC_RESULT` and required library metadata
- [ ] Normalize the Rockwell microsecond calculation to CODESYS milliseconds
- [ ] Generate the CODESYS application-extension function-block POU
- [ ] Generate and resolve the function-block instance call
- [ ] Import, compile and execute in CODESYS with zero errors

### OpenPLC

- [ ] Determine the supported system or host clock API
- [ ] Implement the same neutral `wall_clock_read` capability
- [ ] Select portable IEC types and timestamp units
- [ ] Import or compile an equivalent function block
- [ ] Document runtime and platform limitations

## Phase 4: validation

- [ ] Unit-test rising enable, continuous enable and disable
- [ ] Unit-test interval boundaries and one-scan pulse duration
- [ ] Unit-test clock-read failure behaviour
- [ ] Test timestamp unit conversion explicitly
- [ ] Test clock movement backwards or document it as unsupported
- [ ] Compare generated XML with native CODESYS evidence
- [ ] Perform CODESYS online observation over multiple intervals
- [ ] Record semantic-validation results separately from XML import results

## Deferred: PLCopen Common Behaviour wrapper

`RTC_PulseGen` uses an edge internally to initialize timing, but its public
operation is level-controlled and continuous while enabled. It is therefore
closer to PLCopen `LConC` than to the edge-triggered `ETrig` model.

After the underlying translation is validated:

- [ ] Design an optional level-controlled continuous wrapper
- [ ] Retain the original AOI interface on the internal implementation
- [ ] Define `xValid`, `xBusy`, `xError` and `iErrorID` semantics
- [ ] Keep the application-specific `xPulse` output
- [ ] Confirm whether a wrapper is useful on both CODESYS and OpenPLC
- [ ] Ensure opting out preserves the direct translated interface

The wrapper is intentionally deferred. Standardizing the outer interface
before the clock adapter and pulse semantics are validated would create the
appearance of portability without proving runtime equivalence.

## Out of scope

- Changing the controller's real-time clock
- Treating the RTC function block as a general scheduler
- Assuming all `GSV` instructions are wall-clock reads
- Embedding CODESYS library types in the vendor-neutral controller model
- Special-casing conversion based on an AOI name
