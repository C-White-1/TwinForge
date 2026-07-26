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
