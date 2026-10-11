# A shareable CODESYS library for Machine Expert – Basic blocks

Research notes (2026-10-11) behind the roadmap item "Publishable CODESYS
library". The question: TwinForge generates IEC function blocks that
reproduce Machine Expert – Basic's counter (`%C`) and drum (`%DR`), verified
in the Machine Expert – Basic 3.0 simulator. Should they live in a CODESYS
library that other CODESYS users can install, rather than be copied into
every exported project?

## Is there an existing equivalent?

| Where | Drum sequencer like `%DR`? |
| --- | --- |
| IEC 61131-3 / CODESYS Standard library | No. The Standard library has the IEC basics (timers, counters, edge detection, bistables). Searches found no CODESYS or CODESYS Forge drum block. |
| CODESYS Building Automation `SequenceControl` | No: despite the name, it sequences up to four heating/cooling PID outputs. |
| OSCAT `SEQUENCE_4` / `SEQUENCE_8` | Not equivalent: steps are timed (`WAIT`/`DELAY` per channel, a `START` edge), with no step pattern table and no pulse-driven advance. |
| Siemens S7 | Yes, a standard `DRUM` block (FB 85); other platform. |
| Rockwell | The nearest cousin is `SQO` (sequencer output: one word per step written to an output). |
| **Schneider EcoStruxure Machine Expert (CODESYS-based): TwidoEmulationSupport library** | **Yes: `FB_Drum`.** |

### Schneider's TwidoEmulationSupport library

Source: *EcoStruxure Machine Expert, TwidoEmulationSupport Library Guide*,
EIO0000002956.00 (06/2019), read in full, and the Machine Expert V1.1/V2.0
online help.

- **Purpose:** "the functions and function blocks to convert projects from
  EcoStruxure Machine Expert - Basic / TwidoSoft / TwidoSuite into a
  compatible implementation in EcoStruxure Machine Expert". Project
  conversion maps `%DR` to `FB_Drum`.
- **Schneider's policy is TwinForge's:** a Basic function block is either
  converted "to a type that already exists in EcoStruxure Machine Expert,
  for example the function block exists in the standard library", or "a
  new function block that is fully compatible with EcoStruxure Machine
  Expert - Basic is implemented".
- **`FB_Drum`**
  - Inputs: `i_xReset`; `i_xNextStep`, where a rising edge advances one step "and updates the control bits"; `i_iNumberOfSteps` (1–8); and `i_abyAssignOutputsToSteps` (`ARRAY [0..15] OF BYTE`, "a 8x16 bitmask to assign states to all bit outputs").
  - In/out: `iq_iStepNumberAct`, the current step, which can be written; "the effect takes place on the next execution".
  - Outputs: `q_xFull` and `q_x00`–`q_x15`.
- **`FB_Counter`**
  - It "calls the function block CTUD. The standard CTUD behavior is extended by a preset value handling and Twido-compliant overflow behavior".
  - Inputs: `i_xLoad`, `i_xReset`, `i_xCountUp`, `i_xCountDown`, and `i_iPreset` (default 32767).
  - Outputs: `q_xUnderflow`, `q_xDone`, `q_xOverflow`, and `q_iCounterValue` (documented 0..32767).
  - A selectable maximum, `i_etMaxVal`.
- **Also in the library:**
  - `FB_Timer`: TON/TOF/TP, time bases 1 ms to 1 min, and `i_xRetentive`.
  - `FB_FiFo`/`FB_LiFo`, `FB_ShiftBitRegister` and `FB_StepCounter`.
  - These cover Basic objects TwinForge does not convert yet, including the retentive timer of fixture `05c_timer`.
- **Availability:** it ships with Machine Expert. Nothing found suggests it
  is available to CODESYS targets outside Machine Expert, so it does not
  serve users moving M221 programs to other CODESYS controllers or to
  OpenPLC.

### How Schneider's blocks compare with what the M221 does

- `FB_Drum`'s interface matches TwinForge's: one pattern per drum, up to 8
  steps, 16 bits.
- **Probable behaviour difference (inferred from the documented interface,
  not observed):** `q_x00`–`q_x15` are ordinary outputs, assigned whenever
  the block runs, so whatever a converted project wires them to is written
  every scan. The M221 writes drum outputs only when the step changes (and
  every scan while `R` is held); see
  [the drum checks](../experiments/machine-expert-basic-drum-simulator.md),
  step C2. TwinForge reproduces the M221.
- Schneider's documented counter range (0..32767, selectable maximum)
  differs from the M221's 0..9999 wrap observed in
  [the counter checks](../experiments/machine-expert-basic-counter-simulator.md).
- `FB_Drum` lets logic write the current step. TwinForge supports neither
  logic writing `%DRi.S` nor logic writing `%Ci.P` yet.

## Making and sharing a CODESYS library

From general CODESYS V3 knowledge, not re-checked against CODESYS
documentation:

- A library is a CODESYS *library project* with Project Information
  (company, title, version). Function blocks can be imported from PLCopen
  XML (Project → Import PLCopenXML), which TwinForge already writes.
- It is saved as a `.library` (source readable) or `.compiled-library`
  (source hidden), or installed directly into the Library Repository.
  Projects reference it through the Library Manager by name and version.
- TwinForge should not write the proprietary library file itself: it
  produces the content (PLCopen XML), and CODESYS packages it, by hand or
  through CODESYS's Python scripting engine.

Ways to share (TwinForge is public on GitHub under the MIT licence):

| Route | Notes |
| --- | --- |
| The TwinForge repository (PLCopen XML source plus the built `.library`) | Simplest; MIT allows reuse, modification and redistribution |
| CODESYS Forge | Free community site; better visibility among CODESYS users |
| CODESYS Store | Installable from inside CODESYS; goes through CODESYS GmbH's publishing process (terms for free listings not checked) |

Before publishing:

- **Readable source.** Ship the `.library` (or the PLCopen XML), not only a
  compiled library, so users can check the logic.
- **CODESYS version.** Build with a reasonably old 3.5 service pack; a
  library saved in a newer version may not open in an older one. State it.
- **Naming.** Use a TwinForge name (for example `TwinForge_MEBasic`) and
  describe it as reproducing Machine Expert – Basic `%C`/`%DR` behaviour.
  Avoid Schneider names or branding that suggest Schneider made or endorses
  it.
- **Verification statement.** Each block lists its simulator checklist, the
  recorded sequences its tests replay, and what is not modelled: `%S17`/
  `%S18`, restart effects on outputs, and logic writing a preset or step.
- **No warranty.** The README says plainly that users must test on their own
  equipment (the MIT licence already disclaims warranty).
- **Support expectations.** For example, "provided as-is; issues and
  contributions welcome".

## Merits

- **Fills a gap.** M221 programs are common. Schneider's compatible blocks
  run only inside Machine Expert, and nothing equivalent exists for other
  CODESYS controllers or OpenPLC.
- **The behaviour findings are useful on their own.** The simulator runs
  found places where the Generic Functions Library Guide is wrong or silent:
  `E` sets only on the wrap, counting up clears `E`, `CU`+`CD` in one scan
  cancel, and the drum writes only on a step change but every scan while
  `R` is held.
- **A compile check TwinForge lacks.** The generated Structured Text has so
  far only been parsed by TwinForge's own parser. Compiling it in CODESYS,
  and running the recorded sequences in the CODESYS SoftPLC, would add a
  second oracle.
- **Cleaner exports.** CODESYS projects reference one versioned library
  instead of embedding copies.

Costs: maintenance and support questions once public, and the obligation to
keep its claims accurate (which the evidence trail supports).

## Sources

- TwidoEmulationSupport Library Guide, EIO0000002956.00 (PDF):
  https://download.schneider-electric.com/files?p_Doc_Ref=EIO0000002956&p_File_Name=EIO0000002956.00.pdf&p_enDocType=User+guide
- FB_Drum, Machine Expert V2.0 help:
  https://product-help.schneider-electric.com/Machine%20Expert/V2.0/en/TwiEmSup/TwiEmSup/Advanced_FBs/Advanced_FBs-3.htm
- FB_Counter, Machine Expert V1.1 help:
  https://product-help.schneider-electric.com/Machine%20Expert/V1.1/en/TwiEmSup/TwiEmSup/Standard_FBs/Standard_FBs-3.htm
- Converting Projects, Machine Expert V1.1 help:
  https://product-help.se.com/docs/Machine+Expert/V1.1/en/SoMProg/SoMProg/Managing_Devices/Managing_Devices-11.htm
- CODESYS Building Automation SequenceControl:
  https://content.helpme-codesys.com/en/libs/Building%20Automation/Current/BuildingAutomation/Function-Blocks/Control/SequenceControl.html
- OSCAT SEQUENCE_8: https://oscat.readthedocs.io/projects/oscat-basic/en/latest/Logic/generators/sequence_8/
- Siemens DRUM block: https://instrumentationtools.com/siemens-drum-block-for-sequencer-operation/
