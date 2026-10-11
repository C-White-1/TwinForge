# Machine Expert – Basic drum (`%DR`): simulator checks

Purpose: settle what the Generic Functions Library Guide (EIO0000003289.04,
Drum (%DR): Description, Configuration, Programming Example) leaves
ambiguous, and capture how a `.smbp` file stores a configured drum, before
TwinForge converts `%DR` into a generated IEC function block (as it does for
`%C`; see the [counter checks](machine-expert-basic-counter-simulator.md)).
Run in the Machine Expert – Basic simulator; nothing needs a real controller.

The only drum sample TwinForge has (`ss56/drum-test.smbp`) has an empty
`<Drums />` configuration, so the saved project is needed as much as the
results.

| # | Question | Why it is open |
| --- | --- | --- |
| Q1 | Which output does control bit *n* drive? | The Programming Example says steps 1–6 drive `%Q0.0`–`%Q0.5`, but its own assignment table maps bit 1 to `%Q0.1` and bit 0 to nothing. **Answered by the Drum Assistant:** each of bits 0–15 has its own address box, so a bit drives the address typed beside it; bit 0 is assignable. |
| Q2 | Is `R` level- or edge-triggered? | The Inputs table says "at state 1"; the timing diagram says "rising edge". |
| Q3 | What happens on `U` at the last step, and to `F`? | The timing diagram shows a wrap to step 0; `F` is "current step equals the last step". |
| Q4 | Are the control bits written every scan, or only when the step changes? | Decides what happens when another rung also drives the same output. |
| Q5 | `R` and `U` together: does `R` win? | Not stated. |
| Q6 | When does writing `%DRi.S` take effect? (optional) | The timing diagram: "updated at the next execution time". |

## Setup

1. New project, any TM221 (same as the counter project is fine).
2. Rung 0: a Drum `%DR0`:
   - `%I0.0` → `U`, `%I0.1` → `R`.
   - `F` → `%Q0.7`.
3. Configure `%DR0` in the Drum Assistant: **Number of steps 4**. Rows are
   control bits (an address box each), columns are steps:

   | Row | Address box | Ticked under step |
   | --- | --- | --- |
   | Bit 0 | `%Q0.0` | 1 |
   | Bit 1 | `%Q0.1` | 1 |
   | Bit 2 | `%Q0.2` | 2 |
   | Bit 3 | `%Q0.3` | 3 |

   Step 0 has no ticks; other bits stay blank. So step 0 lights nothing,
   step 1 `%Q0.0` and `%Q0.1`, step 2 `%Q0.2`, step 3 `%Q0.3`.
   **Screenshot the filled-in assistant**: it shows how the file's fields
   map to the configuration.
4. Rung 1 (for Q4): contact `%I0.2` → **reset coil** `(R)` `%Q0.1` (the
   same output as step 1). A reset coil writes only while its contact is
   on, so it shows whether the drum rewrites `%Q0.1` afterwards. (First run
   used a plain coil: it writes 0 every scan after the drum, so `%Q0.1`
   stayed 0 at step 1, see A2.)
5. Animation table: `%DR0.S`, `%DR0.F`, `%Q0.0`, `%Q0.1`, `%Q0.2`,
   `%Q0.3`, `%Q0.7`, and the inputs `%I0.0`–`%I0.2` (to force them).
6. Start the simulator and run. As before, a pulse is Force to 1 then Force
   to 0, and a force stays until you change it.

Save the project as `examples/machine_expert_basic/14_drum_simulation.smbp`.
(The saved fixture has rung 1 as the original plain coil, and rung 2 from the third run.)

## Steps and results

Record `S`, `F` and the outputs after each step (`Q` = which of
`%Q0.0`–`%Q0.3` are on).

| Step | Action | S | F | Q on | Settles |
| --- | --- | --- | --- | --- | --- |
| A1 | Pulse `R` (`%I0.1`) | 0 | 0 | none | baseline |
| A2 | Pulse `U` (`%I0.0`) once | 1 | 0 | `%Q0.0` (plain coil on `%Q0.1` in rung 1) | Q1; a later coil overrides the drum's write in the same scan |
| A3 | Pulse `U` once more | 2 | 0 | `%Q0.2` only | Q1; `%Q0.0` turned off: a step writes 0s too |
| A4 | Pulse `U` once more (last step) | 3 | 1 | `%Q0.3` only (`%Q0.7` on) | Q3: `F` is set while on the last step |
| A5 | Pulse `U` once more | 0 | 0 | none (`%Q0.7` off) | Q3: wraps to step 0, writes step 0's (empty) pattern, `F` clears |
| B1 | Pulse `U` until S = 2 (writing `%DR0.S` is not possible, see D1) | 2 | 0 | `%Q0.2` | |
| B2 | Force `R` to 1 and leave it on; pulse `U` | 0 | 0 | none | Q2: `R` acts while held (an edge-only `R` would let `U` advance to 1); Q5: `R` wins; `R` writes step 0's pattern |
| B3 | Release `R` (force 0) | 0 | 0 | none | |
| C1 | With the reset coil: pulse `U` until S = 1. Force `%I0.2` to 1: `%Q0.1`? | 1 | 0 | `%Q0.0`, `%Q0.1` | Q4 |
| C2 | Force `%I0.2` back to 0, still at S = 1 | 1 | 0 | `%Q0.0` only | Q4: the drum does **not** rewrite `%Q0.1`; outputs are written only when the step changes |
| D1 | (optional) Without touching inputs, write `%DR0.S` = 3 | | | | Q6: not testable; the animation table writes the original step value back |

### Results (2026-10-11, Machine Expert – Basic 3.0 simulator)

- **Q1** Each control bit drives the address in its box (bits 0–15, bit 0
  included); the guide's example table was inconsistent, not the drum.
- **Q2** `R` is level-sensitive: while it is on the drum stays at step 0.
- **Q3** `F` = current step is the last (`StepsNumber - 1`); `U` on the last
  step wraps to step 0 and `F` clears.
- **Q4** On a step change (by `U` or `R`) the drum writes every assigned
  bit to the new step's pattern, 0s included; otherwise it writes nothing,
  so a later write by other logic stands until the next step change. A
  plain coil on the same output, scanned after the drum, overrides it every
  scan (A2).
- **Q5** `R` wins over `U`.
- **Q6** Not testable: the animation table does not accept a `%DRi.S` write.

Third run: while `R` is held the drum writes step 0's pattern every scan
(E1, E1b), even when already at step 0; the step survives a stop/run (E2).
With that, every behaviour the generated block encodes has been observed and
`TF_MEBasic_Drum_<instance>` is marked verified. Restart effects on outputs
are the target runtime's and are not modelled.

### Third run (2026-10-11): the two assumptions

TwinForge's generated block (`TF_MEBasic_Drum_<instance>`) encodes two
behaviours nobody has observed yet; it stays unverified (not exported by
default) until they are. Add rung 2: contact `%I0.3` → **set coil** `(S)`
`%Q0.0`, and add `%I0.3` to the animation table.

| Step | Action | S | F | Q on | Settles |
| --- | --- | --- | --- | --- | --- |
| E1 | Pulse `R`. Force `R` (`%I0.1`) to 1 and leave it on. Pulse `%I0.3` (sets `%Q0.0`). Is `%Q0.0` on? | 0 | 0 | none (`%Q0.0` cleared) | Does `R` held at step 0 rewrite step 0's pattern every scan? (assumed: no, `%Q0.0` stays on). **Assumption wrong:** `R` at step 0 wrote step 0's pattern. Order of forcing uncertain, so E1b decides every scan vs. once when `R` comes on |
| E1b | Keep `R` forced on. Pulse `%I0.3` again (1, then 0). Is `%Q0.0` on? | 0 | 0 | none | **Settled: while `R` is held the drum rewrites step 0's pattern every scan** |
| E2 | Release `R`. Pulse `U` (S = 1). **Stop controller**, then **Run controller** again. S and outputs? | 1 | 0 | `%Q0.0` (`%Q0.1` held off by rung 1's plain coil) | The step is kept across stop/run. Whether outputs are rewritten at start-up cannot be told apart here (`%Q0.0` was already 1); restart behaviour follows the target runtime and is not modelled |

## Notes

- File format (from the saved project): `SoftwareConfiguration/Drums/Drum`
  holds `Address`, `Index`, `StepsNumber`, and `Bits/BitForDrum` ×16, each
  with `Index`, an `Outputs` address (absent when unassigned) and `Steps/Step`
  ×8: `<Used>true</Used>` where ticked, empty when not, and
  `<Available>false</Available>` beyond `StepsNumber`.

Anything surprising, write it here. Screenshots of the Drum Assistant and of
the animation table at A2, A5 and C2 are especially useful.
