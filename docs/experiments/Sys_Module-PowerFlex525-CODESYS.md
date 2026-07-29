# Sys_Module PowerFlex 525 CODESYS experiment

## Objective

Establish a CODESYS EtherNet/IP implementation of the neutral module-service
contract used by the Rockwell `Sys_Module` AOI. The experiment must compare
observable behavior; it must not assume that CODESYS diagnostic values have
the same numeric representation as Logix `MODULE` attributes.

## Current constraint

A physical PowerFlex 525 is not currently available. The experiment is
therefore divided into an offline configuration phase that can be performed
now and a hardware-validation phase that is explicitly deferred.

An offline CODESYS project can prove that the EDS, device description,
generated IEC objects, declarations, and adapter code compile. It cannot
prove successful EtherNet/IP connection behavior, real drive diagnostics,
assembly compatibility, or inhibit/reconnect behavior.

## Source evidence

`Dev_PF525_Program.L5X` is a program export and contains only a reference named
`Dev_PF525`. The sibling `Dev_PF525_Module.L5X` supplies the controller-module
and cyclic connection configuration that is absent from the program export.

The export does show:

- cyclic input and output tags `Dev_PF525:I` and `Dev_PF525:O`;
- a `Sys_Module` call with `Dev_PF525` as its `MODULE` reference; and
- explicit CIP Generic messages using class `16#93`, including a read service
  and a parameter write.

The module export identifies a generic `ETHERNET-MODULE`, not a
PowerFlex-specific Logix profile. It records address `192.168.1.80`, input
assembly 1 with 8 bytes, output assembly 2 with 4 bytes, a 10 ms RPI, unicast
I/O, and disabled electronic keying. These are example configuration values,
not universal drive defaults.

## CODESYS project

1. Create a standard project for the intended CODESYS runtime.
2. Add an Ethernet Adapter beneath the controller.
3. Add an **EtherNet/IP Scanner (IEC)** beneath that adapter.
4. Install the appropriate PowerFlex 525 EDS and add the drive as a remote
   adapter. If a generic remote adapter is used, configure the independently
   evidenced assemblies and sizes above.
5. Enable device diagnosis in the PLC settings. This is required for the
   generated diagnostic IEC objects.
6. On the drive's **IEC Objects** tab, record the generated instance name and
   datatype. The expected diagnostic type is based on
   `IoDrvEtherNetIP.RemoteAdapter_diag`; do not instantiate that driver
   function block manually.

## Offline observation POU

Create a Structured Text POU that exposes, without yet controlling the drive:

- the remote adapter's `eState`;
- `GetDeviceState` result and its `DED.ERROR`;
- `xDiagnosisInfoAvailable`;
- `sDiagString`;
- the `Enable` property; and
- `DED.CanReconfigure` for the corresponding node.

Compile the project and export its PLCopen XML. If CODESYS Control Win permits
the application to run without the remote adapter, record the resulting
not-found or disconnected state as **offline runtime evidence only**.

Do not fabricate a connected state or classify a simulated response as
PowerFlex hardware evidence.

TwinForge can generate an importable normalized binding shell with:

```powershell
uv run python examples/export_codesys_sys_module_binding.py `
  examples/PLCOpenXML/TF_Codesys_SysModule_Binding.xml `
  --device-variable Dev_PF525
```

The generated project contains `TF_Codesys_ENIP_ModuleBinding`, `PLC_PRG`,
and `MainTask`. With `--device-variable`, `PLC_PRG` wires the generated
remote-adapter observations to its `Inp_*` variables and performs the verified
single-call `DED.Reconfigure` handshake. The configured device must already
provide a `RemoteAdapter_diag` object with the supplied variable name.
Omitting the option generates the earlier target-independent shell. Neither
form contains unresolved Rockwell `MODULE`, `GSV`, or `SSV` constructs.

## Deferred hardware observations

When a physical PowerFlex 525 and an isolated test network become available,
capture online values for:

1. drive powered and connected;
2. drive powered off or Ethernet disconnected;
3. connection restored; and
4. drive faulted, if this can be performed safely.

Do not test disable/reconfigure while the drive controls plant equipment.

## Deferred controlled reconfiguration test

With physical hardware, on an isolated test system only:

1. Confirm `DED.CanReconfigure` is `TRUE`.
2. Set the remote adapter's `Enable` property to `FALSE`.
3. Execute `DED.Reconfigure` and record its asynchronous completion/error.
4. Observe adapter state, I/O behavior, and automatic reconnection.
5. Restore `Enable := TRUE`, reconfigure again, and confirm recovery.

This is the candidate mapping for Rockwell inhibit/uninhibit. It is a
normalized behavioral mapping, not proof that CODESYS implements the numeric
Logix `Mode` attribute.

## Evidence to export

Save a PLCopen XML export containing:

- the observation POU;
- its variable declarations;
- any helper function block used for `DED.Reconfigure`;
- the application and task that call it; and
- the generated diagnostic IEC-object references, if CODESYS includes them.

Also record screenshots or text values for every observation state. Name the
PLCopen file `12_enip_remote_adapter_diagnostics.xml`.

## Acceptance criteria

### Offline milestone

- The project compiles with the generated EtherNet/IP diagnostic object.
- The configured assemblies, sizes, and RPI are visible and exportable.
- The observation POU exposes diagnostics without inventing source values.
- The PLCopen export preserves the relevant declarations and calls.

### Hardware milestone

- Connected and disconnected states are distinguishable.
- Diagnostic availability and detail are observable.
- Reconfiguration support is queried before use.
- Disable and re-enable either succeed with explicit completion status or are
  recorded as unsupported.
- No Rockwell `EntryStatus`, `FaultCode`, `FaultInfo`, or `Mode` numeric value
  is fabricated.

## Offline session evidence — 2026-07-28

The generated
`examples/PLCOpenXML/TF_Codesys_SysModule_Binding.xml` project was imported
and built successfully in CODESYS Control Win V3 x64.

A generic EtherNet/IP device named `Dev_PF525` was configured beneath an
EtherNet/IP Scanner with the source-backed connection values:

- address `192.168.1.80`;
- configuration assembly class 4, instance 6, attribute 3;
- consuming O-to-T assembly instance 2 with 4 bytes;
- producing T-to-O assembly instance 1 with 8 bytes;
- cyclic Exclusive Owner connection at 10 ms; and
- generated path `20 04 24 06 2C 02 2C 01`.

CODESYS generated IEC variable `Dev_PF525` with datatype
`RemoteAdapter_diag`. Autocomplete and successful compilation confirmed:

- `Enable`;
- `eState`;
- `GetDeviceInfo`;
- `GetDeviceState`;
- `sDiagString`; and
- `xDiagnosticAvailable`.

The generated `AdapterState` enum documents `RUNNING` as all connections
established, and exposes `BUS_ERROR` and `ERROR` as explicit failure states.
The next session should compile the qualified enum mappings into the binding:

```iecst
xInp_Connected :=
    Dev_PF525.eState = IoDrvEtherNetIP.AdapterState.RUNNING;
xInp_Enabled := Dev_PF525.Enable;
xInp_Faulted :=
    (Dev_PF525.eState = IoDrvEtherNetIP.AdapterState.BUS_ERROR)
    OR (Dev_PF525.eState = IoDrvEtherNetIP.AdapterState.ERROR);
xInp_DiagnosticAvailable := Dev_PF525.xDiagnosticAvailable;
```

The diagnostic property assignments to `Enable`, `sDiagString`, and
`xDiagnosticAvailable` already compile. Reconfiguration and the
`GetDeviceState` signature remain to be verified.

## Completed offline runtime evidence — 2026-07-29

The corrected project evidence is retained in:

- `examples/PLCOpenXML/12_enip_remote_adapter_diagnostics.xml`; and
- `examples/CODESYS/33_sys_module_enip_diagnostics.export`.

The installed target resolved CAA Device Diagnosis 3.5.22.0 and
IoDrvEtherNetIP 4.9.0.0. The following expressions compiled and ran:

```iecst
eObservedDeviceState := Dev_PF525.GetDeviceState();
xInp_CanReconfigure :=
    DED.CanReconfigure(itfNode := Dev_PF525);
```

The passive offline state was:

- `AdapterState.NOT_CONFIGURED`;
- `DED.DEVICE_STATE.NOT_CONFIGURED`;
- enabled and reconfigurable;
- not connected and not faulted;
- no diagnostic string; and
- `DED.ERROR.NO_ERROR`.

A rising inhibit command set `Dev_PF525.Enable` to `FALSE`, completed
`DED.Reconfigure` without error, and produced both
`AdapterState.DISABLED` and `DED.DEVICE_STATE.DISABLED`. After releasing the
shared command edge, a rising uninhibit command restored `Enable` to `TRUE`
and both state models returned to `NOT_CONFIGURED`, as expected without a
physical adapter.

The final program calls `DED.Reconfigure` exactly once per scan. It supplies
the prior asynchronous busy, done, and error outputs to the neutral binding,
executes the binding, applies the requested `Enable` value, and then calls
the reconfiguration function block.

This proves the offline CODESYS node behavior only. It does not prove a
PowerFlex connection, cyclic assembly exchange, drive response, or numeric
equivalence with Rockwell `Mode`.
