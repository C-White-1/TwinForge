# Dvc_PF525 conversion-readiness report

## Decision

The source is classified `adapter_required` and should become an IEC `function_block`. Conversion is feasible as a staged implementation; direct translation alone is not sufficient.

- Unresolved dependencies: 0
- Unanalyzed routines: 0
- Directly portable areas: 1
- Datatype/instruction adaptations: 3
- Target-adapter areas: 3
- Manual-review areas: 1
- Hardware-validation areas: 1

## Readiness matrix

| Area | Classification | Implementation action | Evidence | Completion criterion |
| --- | --- | --- | --- | --- |
| Core command and speed logic | `direct_portable` | Lower command arbitration, permissive/interlock equations, run/jog latches, start timing, speed limiting, and tracking to vendor-neutral executable IR and IEC Structured Text. | all implementation routines are captured as Structured Text; no unresolved AOI dependencies | IEC unit tests reproduce the captured equations and state transitions without target services. |
| Cyclic I/O datatypes | `type_adaptation` | Replace generated Logix module datatypes with neutral status and command structures while preserving byte and bit layout. | input point 1, 8 bytes; output point 2, 4 bytes | Round-trip layout tests prove every status and command field occupies the documented byte and bit position. |
| Rockwell data operations | `type_adaptation` | Lower COP, SIZE, SWPB, TONR, and Logix bit overlays to typed IEC operations with explicit endian and bounds behavior. | COP; SIZE; SWPB; TONR | Golden-vector tests cover copy length, array bounds, byte order, timer state, and signed 16-bit conversions. |
| Lifecycle behavior | `type_adaptation` | Map the captured Prescan initialization and read-sequence resets while preserving run/timer state unless an explicit target lifecycle policy requires otherwise. | prescan | Cold start, warm restart, disabled execution, and re-enable tests match the retained-state contract. |
| Explicit parameter messaging | `target_adapter` | Define a neutral parameter read/write service and implement separate CODESYS and future OpenPLC providers. | MESSAGE datatype; MSG service; CIP class 0x93 | A mock provider passes deterministic read/write sequencing tests before any target-specific network implementation. |
| Module identity, status, and inhibit services | `target_adapter` | Bind the neutral module-service contract to target-specific connection diagnostics and supported control operations. | MODULE datatype; Sys_Module GSV/SSV; 8 diagnostic indicators | Each source property is classified equivalent, approximated, unavailable, or blocking for the selected target. |
| Wall-clock pulse generation | `target_adapter` | Use the validated RTC_PulseGen target implementation behind a neutral pulse/timing contract. | RTC_PulseGen dependency; wall_clock_read capability | Target trace confirms pulse interval and restart behavior. |
| Functional and safety intent | `manual_review` | Resolve open AOI QA findings before claiming semantic equivalence, especially the commented IntlkOK conditions. | PF525-QA-020; PF525-QA-021; no PLCopen Common Behaviour match | The responsible engineer records the intended interlock and safety behavior without silently changing source semantics. |
| Drive and network behavior | `hardware_validation` | Commission against a PowerFlex 525 or approved test setup, including cyclic control, faults, C143/C144, explicit parameters, recovery, and inhibit behavior. | offline L5X evidence only; no physical PowerFlex 525 currently available | A signed test record demonstrates safe behavior in normal and abnormal operating states. |

## Dependency plan

| Dependency | Classification | Action |
| --- | --- | --- |
| `Math_Epsilon` | `direct_portable` | Emit as portable IEC helper logic. |
| `Msg_SetParams` | `target_adapter` | Replace MESSAGE mutation with neutral request construction. |
| `Msg_SetPathToModule` | `target_adapter` | Move routing and module-path resolution into the target provider. |
| `Op_CmdSrc` | `type_adaptation` | Port stateful arbitration and map Prescan explicitly. |
| `RTC_PulseGen` | `target_adapter` | Reuse the validated target clock implementation. |
| `Str_Size` | `direct_portable` | Lower through the existing array-bounds translation. |
| `Sys_Dvc` | `target_adapter` | Separate portable device status from controller-object metadata. |
| `Sys_Module` | `target_adapter` | Bind the neutral module-service contract. |
| `ST_Dvc_PF525` | `type_adaptation` | Emit neutral nested drive data structures. |
| `ST_Sys_DeviceClass` | `type_adaptation` | Emit the captured classification structure or a neutral mapping. |

## Recommended implementation order

1. Freeze the neutral interfaces and datatype layouts.
2. Port and unit-test the core function-block logic.
3. Implement instruction and lifecycle adaptations.
4. Implement a mock parameter-service and module-service adapter.
5. Generate and compile the PLCopen/CODESYS project.
6. Run target-runtime integration tests.
7. Complete manual design review and hardware commissioning.

## Architecture boundary

The generated IEC function block should depend on neutral cyclic-I/O, parameter-service, module-service, and timing contracts. CODESYS implementations belong in a CODESYS adapter module; a later OpenPLC implementation can satisfy the same contracts independently.

No adapter may return invented healthy values or silently ignore unsupported inhibit, fault, or write operations.
