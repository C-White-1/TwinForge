# Per-fixture L5X RLL coverage

Source corpus: `tests/data`

Coverage means executable by the current PLCopen/CODESYS lowering; it is
not a claim of general Logix compatibility.

## `aoi/controller_object_services.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `aoi/dependencies_and_locals.L5X`

- Target: Parse failure
- Executable rungs: Not measured
- Executable instructions: Not measured
- Notes: L5X Program export requires exactly one Use='Target' element; found
  0

## `aoi/lifecycle_in_routines.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `aoi/prescan_input_write.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `aoi/rtc_pulse.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `aoi/scan_mode_routines.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `aoi/Str_Capacity_AOI.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `basic/BoosterCompressor_20260128.L5X`

- Target: Controller
- Executable rungs: 134/134
- Executable instructions: 474/474
- Notes: 0 blocking rung(s)

## `openplc/native_boolean.L5X`

- Target: Controller
- Executable rungs: 1/1
- Executable instructions: 2/2
- Notes: 0 blocking rung(s)

## `regression/unknown_content.L5X`

- Target: Program
- Executable rungs: 1/1
- Executable instructions: 2/2
- Notes: 0 blocking rung(s)

## `standalone/aoi.L5X`

- Target: AddOnInstructionDefinition
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `standalone/module.L5X`

- Target: Module
- Executable rungs: Not applicable
- Executable instructions: Not applicable
- Notes: No controller/program RLL body

## `standalone/program.L5X`

- Target: Program
- Executable rungs: 0/0
- Executable instructions: 0/0
- Notes: 0 blocking rung(s)
