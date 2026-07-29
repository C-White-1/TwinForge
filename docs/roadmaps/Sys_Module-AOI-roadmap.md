# Sys_Module AOI conversion roadmap

This roadmap tracks conversion of the Rockwell `Sys_Module` Add-On
Instruction from `Dev_PF525_Program.L5X`. The objective is to preserve its
portable status logic while keeping controller-managed module services behind
an explicit target adapter.

## Captured behavior

`Sys_Module`:

- accepts a Rockwell `MODULE` reference;
- reads `INSTANCE`, `EntryStatus`, `FaultCode`, `FaultInfo`, and `Mode` using
  `GSV`;
- writes `Mode` using `SSV` to inhibit or uninhibit the module;
- uses a retained one-shot state for the two command inputs;
- decodes the high nibble of `EntryStatus` into named Boolean states; and
- resets command, status, and diagnostic values in Prescan.

The status decoding and command-edge logic are portable IEC Structured Text.
The `MODULE`, `GSV`, and `SSV` behavior is a controller-runtime capability,
not ordinary IEC logic.

## Phase 1: neutral capture and executable IR

- [x] Capture parameters, local tags, Logic, and Prescan
- [x] Preserve the documented absence of `DataType` on alias parameters
- [x] Resolve aliases such as `Sts_Connected -> Status.4` to effective
  datatype `BOOL`
- [x] Keep Prescan-only input assignments from changing the cyclic interface
- [x] Lower module `GSV` calls to structured controller-object reads
- [x] Lower module `SSV` calls to structured controller-object writes
- [x] Preserve object class, instance operand, attribute, destination/value,
  and source vendor
- [x] Reduce current export diagnostics to one honest
  `controller_object_access` target requirement

## Phase 2: vendor-neutral module-service contract

- [x] Define a module identity/reference contract independent of Logix
  `MODULE`
- [x] Define readable intents for instance, connection status, fault code,
  fault information, and mode
- [x] Define an inhibit command intent while preserving the raw source value
- [x] Separate raw source status values from normalized connection health
- [x] Classify unavailable and bus-specific target attributes explicitly
- [x] Avoid claiming that a CODESYS device-tree object is interchangeable with
  a Logix Module object

## Phase 3: CODESYS evidence and adapter

- [x] Identify CAA Device Diagnosis and bus-specific device IEC objects
- [x] Establish that runtime enable/disable is bus-driver-specific
- [x] Define the native CODESYS EtherNet/IP diagnostic experiment
- [x] Separate the reusable CODESYS EtherNet/IP adapter from device profiles
- [x] Run the offline native CODESYS EtherNet/IP diagnostic experiment
- [x] Export its PLCopen XML, native configuration, and library metadata
- [x] Map supported normalized reads through the target adapter
- [x] Preserve unsupported reconfiguration as an explicit blocking
  requirement
- [x] Generate a compilable normalized binding function block without
  unresolved `MODULE` types
- [x] Import, compile, and observe offline `NOT_CONFIGURED` and `DISABLED`
  states
- [ ] Observe connected, disconnected, and faulted states with hardware

## Phase 4: validation

- [x] Unit-test every `EntryStatus` state mapping
- [x] Unit-test inhibit and uninhibit rising-edge behavior
- [x] Unit-test Prescan reset behavior
- [x] Unit-test target-service success and failure through the vendor-neutral
  adapter boundary
- [ ] Compare target diagnostics with Rockwell source semantics
- [ ] Record which properties are equivalent, approximated, or unavailable

## Deferred PowerFlex AOI engineering outputs

- [x] Analyze the cyclic input/status and output/command contract
- [x] Generate a focused diagnostic and fault report
- [x] Generate a PowerFlex functional description from captured behavior
- [x] Classify PowerFlex conversion readiness and implementation order
- [x] Define target-neutral cyclic-I/O layouts and runtime service contracts
- [x] Verify the captured 8-byte status and 4-byte command packing
- [x] Port and behavior-test the target-neutral Dvc_PF525 command core
- [x] Emit the neutral command core as IEC Structured Text
- [x] Package the core with PLC_PRG and MainTask for CODESYS import
- [x] Import and compile the generated PowerFlex core in CODESYS
- [x] Capture and inventory a native CODESYS PowerFlex test visualization
- [x] Decode the verified geometry, text, binding, action, and InputBox subset
  using controlled differential exports
- [ ] Expand the profile map for remaining opaque visualization properties
- [x] Define a target-neutral visualization model
- [x] Generate a native CODESYS visualization only after profile compatibility
  and round-trip behavior are verified
- [x] Implement a source-backed SP22 exporter for the verified existing-control
  subset
- [x] Import and inspect the unchanged source-backed round-trip in CODESYS
- [x] Verify a deliberately modified source-backed export in CODESYS
- [ ] Complete hardware-dependent EtherNet/IP and drive validation when a
  suitable PowerFlex 525 test installation is available

## Current boundary

TwinForge can now parse, type, lower, and emit all portable `Sys_Module`
logic without false unresolved-expression or unknown-datatype diagnostics.
Emission remains incomplete solely because no CODESYS implementation of the
neutral `controller_object_access` capability has yet been established.

TwinForge also provides a CODESYS EtherNet/IP implementation of the narrower
normalized `ModuleService` contract. This supports connection and diagnostic
observation plus capability-gated reconfiguration requests, but it is not
substituted for raw Rockwell controller-object access.

This is intentional. Returning constant “healthy” values or silently ignoring
module inhibit commands would produce compilable XML with unsafe semantics.

Official CODESYS evidence shows that connection health can be normalized
through CAA Device Diagnosis, whereas detailed state, fault data, identity,
and runtime device control depend on the configured bus driver. For example,
`DED.Reconfigure` supports runtime enable/disable for documented PROFINET
configurations; this is not evidence of a universal CODESYS inhibit service.

For the PowerFlex target, CODESYS generates a
`IoDrvEtherNetIP.RemoteAdapter_diag` IEC object. Official library metadata
shows that it provides adapter state, CAA Device Diagnosis, diagnostic text,
an `Enable` property, and `IReconfigureProvider`. TwinForge therefore records
an EtherNet/IP-specific normalized mapping, while retaining the generic
bus-specific boundary.
