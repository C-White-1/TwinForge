# CODESYS EtherNet/IP module adapter

TwinForge separates CODESYS EtherNet/IP runtime services from the profile of
any particular remote device. The adapter proven during the PowerFlex 525
experiment is therefore reusable infrastructure, not a PowerFlex-only
implementation.

## Architecture layers

The integration has four distinct responsibilities:

| Layer | Responsibility | Example |
| --- | --- | --- |
| Neutral runtime contract | Connection health and enable-state intent without target types | `ModuleService` |
| CODESYS EtherNet/IP adapter | Translate generated IEC diagnostics and reconfiguration into the neutral contract | `RemoteAdapter_diag`, `DED.Reconfigure` |
| Device profile | Describe assemblies, cyclic layouts, scaling, and device semantics | PowerFlex 525 profile |
| Deployment instance | Supply configured address, timing, name, and installation-specific choices | `Dev_PF525` at `192.168.1.80` |

This separation prevents a device-specific assembly layout from becoming a
property of every EtherNet/IP adapter. It also prevents CODESYS library types
from entering the vendor-neutral model.

## Reusable CODESYS behavior

When CODESYS generates a `RemoteAdapter_diag` IEC object for a remote
EtherNet/IP device, the target adapter can use the following verified
capabilities:

- `Enable` for the configured node's requested enabled state;
- `eState` for EtherNet/IP-specific adapter state;
- `GetDeviceState()` for normalized `DED.DEVICE_STATE`;
- `xDiagnosticAvailable` and `sDiagString` for diagnostic evidence;
- `DED.CanReconfigure()` for capability detection; and
- one edge-triggered `DED.Reconfigure` instance for asynchronous application
  of configuration changes.

The adapter maps these capabilities to normalized connection, enabled, fault,
diagnostic, and reconfiguration results. The asynchronous function block is
called exactly once per scan. Its prior busy, done, and error outputs are
supplied to the neutral binding before the next request is evaluated.

This behavior can support drives, remote I/O, valve manifolds, instruments,
and other EtherNet/IP targets when their CODESYS device descriptions generate
the required diagnostic object. Reconfiguration remains capability-gated:
TwinForge must not assume that every fieldbus driver or device supports it.

## Generated integration

TwinForge can emit either a portable binding shell or a fully wired CODESYS
target adapter. After CODESYS has generated a `RemoteAdapter_diag` object,
pass its IEC variable name to the exporter:

```powershell
uv run python examples/export_codesys_sys_module_binding.py `
  examples/PLCOpenXML/TF_Codesys_SysModule_Binding.xml `
  --device-variable Dev_PF525
```

The generated `PLC_PRG` observes the native adapter, calls the neutral binding,
applies its requested `Enable` value, and calls one `DED.Reconfigure` instance
exactly once per scan. The configured device must already supply the CODESYS
EtherNet/IP and CAA Device Diagnosis library types. Omitting
`--device-variable` retains the target-independent test shell.

The variable name is configurable: `Dev_PF525` is deployment evidence from
the experiment, not a PowerFlex dependency in the generator.

## Device-profile behavior

A device profile supplies information that cannot be inferred from the
generic adapter:

- assembly instances and connection paths;
- producing and consuming image sizes;
- byte, word, and bit layouts;
- byte order and signedness;
- engineering scaling and units;
- command and status meanings;
- electronic-keying requirements;
- device-specific parameters and explicit messaging; and
- safety or operational constraints.

For the captured PowerFlex example, the profile evidence is configuration
assembly 6, consuming assembly 2 with four bytes, and producing assembly 1
with eight bytes. The output image contains a logic command and speed command;
the input image contains a four-byte pad, drive status, and output-speed
feedback.

Those values describe the captured generic-module configuration. They are not
asserted as universal defaults for every PowerFlex 525 installation.

## Deployment behavior

Addresses, configured names, RPIs, unicast choices, and selected network
interfaces belong to a deployment instance. The example address
`192.168.1.80` and 10 ms RPI came from the source L5X and must not be copied
blindly into another installation.

Electronic keying is also deployment evidence. The captured Logix module had
keying disabled, so its generic identity values do not establish the actual
identity of every compatible drive.

## Equivalence boundary

The CODESYS adapter is behaviorally useful but does not reproduce Rockwell
controller-object values:

- `AdapterState` is not Rockwell `EntryStatus`;
- `DED.DEVICE_STATE` is a normalized state, not a Logix status word;
- CODESYS diagnostic text is not `FaultCode` or `FaultInfo`; and
- `Enable` plus `DED.Reconfigure` is not the numeric Rockwell `Mode`
  attribute.

TwinForge preserves this distinction by implementing the normalized
`ModuleService` contract rather than fabricating a raw `SysModuleSnapshot`.
Hardware testing may establish behavioral equivalence for a specific device,
but it cannot make the underlying representations identical.

### Recorded equivalence

Capability and equivalence are classified separately. `Normalized` support
means TwinForge has an established target API; it does not mean the returned
representation is identical to Rockwell.

| Rockwell intent | CODESYS evidence | Support | Equivalence |
| --- | --- | --- | --- |
| Module instance | `GetDeviceInfo()` identity | Normalized | Approximated |
| `EntryStatus` | `eState` and `GetDeviceState()` | Normalized | Approximated |
| `FaultCode` | CAA Device Diagnosis error | Normalized | Approximated |
| `FaultInfo` | Diagnostic availability and text | Normalized | Approximated |
| Numeric `Mode` | `Enable` and device state | Normalized | Approximated |
| Set inhibited | `Enable`, capability check, and `DED.Reconfigure` | Normalized | Hardware validation required |
| Other source-specific attributes | None established | Unavailable | Unavailable |

No row is classified as exactly equivalent. Offline execution established
that enable and disable requests move the generated adapter between
`NOT_CONFIGURED` and `DISABLED` without errors. It did not establish physical
drive I/O behavior, connection recovery, or equivalence to a Logix `Mode`
write.

The table is rendered from the same classifier used by TwinForge and is
protected by a synchronization test. A standalone copy can be generated with:

```powershell
uv run python examples/export_codesys_module_equivalence.py `
  reports/Dev_PF525_Program/sys_module_codesys_equivalence.md
```

## Evidence

The offline experiment and its limitations are recorded in
[`Sys_Module-PowerFlex525-CODESYS.md`](../experiments/Sys_Module-PowerFlex525-CODESYS.md).
Its canonical fixtures are:

- `examples/PLCOpenXML/12_enip_remote_adapter_diagnostics.xml`; and
- `examples/CODESYS/33_sys_module_enip_diagnostics.export`.

The experiment verified successful compilation, capability detection, node
disable, and node re-enable without a physical PowerFlex drive. Connected,
cyclic-I/O, device-fault, and physical-drive behavior remain hardware
milestones.
