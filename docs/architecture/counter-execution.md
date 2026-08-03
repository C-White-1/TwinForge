# Counter execution and target lowering

## Purpose

TwinForge must preserve a source counter's shared state when more than one
instruction references the same counter tag. This is especially important for
Rockwell ladder logic, where `CTU`, `CTD`, and `RES` can operate on one
`COUNTER` structure.

The captured `Tag` and ordered `LadderRung` objects remain the source of truth.
The vendor-neutral model does not acquire OpenPLC block names or Rockwell-only
status fields. A target adapter may construct a counter state machine only
after it has resolved all instructions that reference the same captured tag.

## Shared state contract

One lowered counter state owner carries:

| Neutral meaning | Rockwell evidence | OpenPLC compatibility port |
| --- | --- | --- |
| accumulated value | `.ACC` | `CV` |
| preset value | `.PRE` | `PV` |
| count-up condition | CTU rung condition and `.CU` | `CU` / `CUEnabled` |
| count-down condition | CTD rung condition and `.CD` | `CD` / `CDEnabled` |
| done state | `.DN` | `Q` |
| overflow latch | `.OV` | `OV` |
| underflow latch | `.UN` | `UN` |
| reset condition | `RES(counter)` | `RESET` |

The OpenPLC implementation name is target-specific and is not part of this
contract. Its state must be owned once per source counter tag, never once per
CTU or CTD occurrence.

## Execution rules

The initial compatibility subset uses these rules:

1. On first execution, initialize the accumulator and status from captured
   decorated tag evidence. Initialize edge memory from the current count
   inputs so an already-true input does not create a false first-scan count.
2. On a false-to-true count-up transition, increment the signed-DINT
   accumulator. Roll over from 2,147,483,647 to -2,147,483,648 and latch
   overflow.
3. On a false-to-true count-down transition, decrement the accumulator. Roll
   over from -2,147,483,648 to 2,147,483,647 and latch underflow.
4. Re-evaluate done state after a count operation as `ACC >= PRE`.
5. Reset clears count-enable, done, overflow, and underflow state and sets the
   accumulator to zero.
6. When both transitions occur in one scan, preserve their source rung order.

These rules are derived from Rockwell's CTU, CTD, and RES instruction
documentation. They are compatibility behavior, not a claim that all vendors
use the same counter semantics.

## Initial supported source shapes

Standalone down-counter:

```text
XIC(count_down)CTD(counter,?,?);
XIC(counter.DN)OTE(done);
XIC(reset)RES(counter);
```

Paired counter, with either CTU or CTD first:

```text
XIC(count_up)CTU(counter,?,?);
XIC(count_down)CTD(counter,?,?);
XIC(counter.DN)OTE(done);
XIC(reset)RES(counter);
```

The initial adapter rejects rather than guesses when:

- CTU and CTD reference different counter tags within the candidate group;
- reset is absent or not adjacent;
- another instruction writes a counter member;
- multiple routines share the counter;
- count conditions exceed the evidenced single-XIC shape; or
- source ordering cannot be represented by one state-owner call.

## Evidence boundary

The native OpenPLC `CTD_DINT` fixture establishes that its `CV` saturates at
zero. It does not establish Rockwell behavior. The current L5X corpus contains
no CTU or CTD rung, so synthetic L5X-shaped model fixtures must be identified
as specification tests until a real source example is added.

Rockwell reference:

- [Count Down (CTD)](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/timer-and-counter-instructions/count-down--ctd-.html)
- [Count Up (CTU)](https://www.rockwellautomation.com/en-id/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/timer-and-counter-instructions/count-up--ctu-.html)
