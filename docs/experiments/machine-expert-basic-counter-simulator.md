# Machine Expert – Basic counter (`%C`): simulator checks

Purpose: settle four points the Generic Functions Library Guide
(EIO0000003289.04, Counter (%C): Description, Configuration) leaves
ambiguous, before TwinForge converts `%C` into a generated IEC function
block. Run in the Machine Expert – Basic simulator; nothing needs a real
controller.

| # | Question | Why it is open |
| --- | --- | --- |
| Q1 | When is `E` set: on *reaching* 0 counting down, or only on the 0 → 9999 wrap? | The Description page says "when the counter reaches 0 value"; the Operations table says "when %Ci.V changes from 0 to 9999". |
| Q2 | Does `E` clear when counting down continues after the wrap? | The Operations table says continuing resets "%Ci.F (down-counting overflow)", which reads like a typo for `E`. |
| Q3 | Does `D` clear when the value moves off the preset? | The guide only says `D` = 1 when `%Ci.V` = `%Ci.P`. |
| Q4 | What does a rising edge on `CU` and `CD` in the same scan do? | Not described. |
| Q5 | When does a changed preset take effect? (optional) | "When the block is processed (activation of one of the inputs)". |

## Setup

1. New project, TM221CE16R (any M221 is fine).
2. One rung with a Counter `%C0`, **Preset = 3**:
   - `%I0.0` → `CU`, `%I0.1` → `CD`, `%I0.2` → `R`, `%I0.3` → `S`.
   - `D` → `%Q0.0`, `E` → `%Q0.1`, `F` → `%Q0.2` (or just watch the bits).
3. For Q4, add a second rung: `%I0.4` wired to **both** `CU` and `CD` of
   another counter `%C1` (Preset 3), or to both pins of `%C0` if the editor
   allows it.
4. Animation table: `%C0.V`, `%C0.P`, `%C0.D`, `%C0.E`, `%C0.F`
   (and `%C1.V` for Q4).
5. Start the simulator, log in, run. Toggle inputs in the simulator's I/O
   panel. A "pulse" is input on, then off.

Save the project as `examples/machine_expert_basic/13_counter_simulation.smbp`
so it joins the fixtures.

## Steps and results

Before each part, pulse `R` (`%I0.2`) so `V` = 0, unless the part says
otherwise. Record `V`, `D`, `E`, `F` after each step.

| Step | Action | V | D | E | F | Settles |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Pulse `CU` ×3 (V should reach 3 = preset) | 3 | 1 | 0 | 0 | baseline |
| A2 | Pulse `CU` once more (V 3 → 4) | 4 | 0 | 0 | 0 | Q3 |
| A3 | Pulse `CD` once (V 4 → 3) | 3 ¹ | 1 | 0 | 0 | Q3 (D on equality from above) |
| B1 | `R`; pulse `CU` once (V = 1); pulse `CD` once (V 1 → 0) | 0 | 0 | 0 | 0 ² | Q1 (E on *reaching* 0?) |
| B2 | Pulse `CD` once more (V 0 → 9999) | 9999 | 0 | 1 | 0 | Q1 (E on the wrap?) |
| B3 | Pulse `CD` once more (V 9999 → 9998) | 9998 | 0 | 0 | 0 | Q2 |
| C1 | Set Preset to 9999 (animation table `%C0.P`, or configuration); pulse `S` (V should become 9999, D = 1) | 9999 | **0** | **1** | 0 | S behaviour |
| C2 | Pulse `CU` once (V 9999 → 0) | 0 | 0 | 0 | 1 | F on the up wrap |
| C3 | Pulse `CU` once more (V 0 → 1) | 1 | 0 | 0 | 0 | F clears? |
| D1 | `R`; pulse `%I0.4` (rising edge on CU and CD together) | 0 ³ | 0 | 0 | 0 | Q4 |
| E1 | Hold `R` and `S` on together | | | | | R priority (guide says R wins) |
| F1 | (optional) Preset back to 3, `R`, pulse `CU` ×2 (V = 2). Set `%C0.P` = 2 in the animation table without touching inputs: read D. Then pulse `CU`. | | | | | Q5 |

### First run (2026-10-10, Machine Expert – Basic 3.0 simulator)

Recorded by the user; E1 and F1 not yet run.

¹ Reported as V = 4; read as 3, since the step is one `CD` from 4 and D = 1
  (D is 1 only on equality with the preset).
² Values other than E not reported for B1; V = 0 by construction.
³ Reported as `%C0.V`; the `%I0.4` rung drives `%C1`, so this needs
  confirming against `%C1`.

What this settles:

- **Q1:** `E` is set only on the 0 → 9999 wrap, not on reaching 0 (B1, B2).
  The Operations table is right; the Description page's "reaches 0" is not.
- **Q2:** `E` clears on the next count down (B3). It also clears on a count
  up (C2), which neither page says.
- **Q3:** `D` follows equality both ways: clears off the preset (A2) and sets
  again on reaching it from above (A3).
- **Q4:** one `CU` and one `CD` edge in the same scan leave V unchanged from 0
  with no flags (D1, pending ³). From 0 this cannot tell "cancel" from
  "up then down"; G2 below can.
- **C1 does not match the guide**, which says `S` loads the preset and sets
  `D`. The recorded V 9999, D 0, E 1 is exactly what `R` then one `CD`
  gives with preset 3, so the preset change or the input pulsed may not
  have been what was intended. Re-run as C1′.

### Second run (2026-10-10)

Run on `%C1` and a third counter `%C2` added for E1, inputs forced from the
animation table (a force persists until released, so a pulse is force 1
then force 0). F1 (Q5, preset timing) not run: it matters only when logic
writes `%Ci.P`, and the export currently passes the configured preset as a
constant `PV`, so preset writes from logic are not yet covered.

Outcome: every behaviour the generated block encodes has been observed, and
`TF_MEBasic_Counter` is marked verified (`exporters/plcopen_library.py`;
replayed in `tests/test_export_plcopen_generated_blocks.py`).

| Step | Action | V | D | E | F | Settles |
| --- | --- | --- | --- | --- | --- | --- |
| C1′ | Preset 3: `R`, then pulse `S` (`%I0.3`) only | **0** (no change) | ? | ? | ? | S loads P, sets D |
| C1‴ | Repeat on `%C1` (preset 3): force `%I0.6` (`R`) 1 then 0, then `%I0.5` (`S`) 1 then 0 | 3 | 1 | 0 | 0 | S loads P, sets D: **confirmed**. C1′ on `%C0` most likely had `R` still forced (forces persist until released) |
| C1″ | Set `%C0.P` = 9999 and **check the table shows 9999**; `R`; pulse `S` | 9999 | ? | ? | ? | S with preset 9999 |
| D1′ | Add `%C1.E`, `%C1.F` to the table. `R` (`%I0.6`), then pulse `%I0.4`; read `%C1.V/E/F` | 0 | 0 | 0 | 0 | Q4 from 0: V unchanged, no flags (cancel and up-then-down agree here) |
| G1 | `%C0`: set `%C0.V` = 9999 in the table, pulse `CU` (V 0, F 1), then `CD` | 9999 | 0 | 1 | 0 | CD clears F: **confirmed** |
| G2 | Set `%C1.V` = 9999 in the table, then pulse `%I0.4` | 9999 | 0 | 0 | 0 | Q4: **simultaneous edges cancel** (up-then-down would set E, down-then-up would give 0 with F) |
| E1 | Hold `R` and `S` on together (wired: `%I0.7` → `R` and `S` of `%C2`, preset 3; `%I0.7` forced to 1) | 0 | 0 | 0 | 0 | R priority: **confirmed**, R wins |
| F1 | As F1 above | | | | | Q5 |

## Notes

Anything surprising (a step the simulator refuses, a value that changes
without an input edge), write it here. Screenshots of the animation table
at A2, B1, B2 and C2 are especially useful.
