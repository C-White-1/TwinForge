# PowerFlex 525 reference provenance

TwinForge uses an ignored local reference bundle for analysis of a PowerFlex
525 represented in Logix as a generic EtherNet/IP module. The files were
obtained from the MIT-licensed
[`JeremyMedders/LogixLibraries`](https://github.com/JeremyMedders/LogixLibraries)
repository:

- [`Dev_PF525_Module.L5X`](https://github.com/JeremyMedders/LogixLibraries/blob/main/src/Device/Rockwell/PowerFlex%20525/Dev_PF525_Module.L5X)
- [`Dev_PF525_Program.L5X`](https://github.com/JeremyMedders/LogixLibraries/blob/main/src/Device/Rockwell/PowerFlex%20525/Dev_PF525_Program.L5X)
- [`Dvc_PF525_AOI.L5X`](https://github.com/JeremyMedders/LogixLibraries/blob/main/src/Device/Rockwell/PowerFlex%20525/Dvc_PF525_AOI.L5X)
- [`520-um001_-en-e.pdf`](https://github.com/JeremyMedders/LogixLibraries/blob/main/src/Device/Rockwell/PowerFlex%20525/520-um001_-en-e.pdf)
- [`520com-um001_-en-e.pdf`](https://github.com/JeremyMedders/LogixLibraries/blob/main/src/Device/Rockwell/PowerFlex%20525/520com-um001_-en-e.pdf)

The L5X source files are covered by the repository licence. The two PDFs are
Rockwell Automation publications and retain their original copyright. They
are local reference material, are excluded by TwinForge's `/reference/`
ignore rule, and are not redistributed by this repository.

## Evidence roles

The files provide different evidence and must not be conflated:

| File | Evidence |
| --- | --- |
| `Dev_PF525_Module.L5X` | Logix controller-module and cyclic connection configuration |
| `Dev_PF525_Program.L5X` | Program integration, AOI invocation, tags, and explicit CIP messages |
| `Dvc_PF525_AOI.L5X` | Device behavior and PowerFlex I/O interpretation |
| `520-um001_-en-e.pdf` | PowerFlex 520-series drive behavior and parameters |
| `520com-um001_-en-e.pdf` | EtherNet/IP adapter configuration and protocol behavior |

The bundle identifies the asset as a PowerFlex 525. The module export alone
does not: it describes a generic `ETHERNET-MODULE`.

## Confirmed controller representation

The module export records:

- module name `Dev_PF525`;
- generic catalog profile `ETHERNET-MODULE`;
- IPv4 address `192.168.1.80`;
- electronic key state `Disabled`;
- input assembly/connection point `1`, size 8 bytes;
- output assembly/connection point `2`, size 4 bytes;
- requested packet interval 10,000 microseconds (10 ms); and
- unicast cyclic I/O.

The program export also records CIP Generic messaging to class `16#93`.

These values describe one example configuration, not universal PowerFlex 525
defaults.

## TwinForge model interpretation

TwinForge represents the PowerFlex 525 as a `Device`. Its Logix
`ETHERNET-MODULE` is a separate `Module`, linked through a
`DeviceModuleBinding`. EtherNet/IP/CIP is a `CommunicationInterface` owned by
the device. The binding does not copy the generic module's identity into the
physical device identity.

`Dvc_PF525` is represented once as a `SoftwareComponent` of kind
`function_block`, with the captured `AddOnInstruction` as its implementation.
Evidence-bearing `SoftwareBinding` records then link that definition to:

- the PowerFlex 525 `Device` using role `device_implementation`;
- `Dev_PF525` using role `module_access`; and
- the `Dvc` tag using role `instance_tag`.

The AOI definition and its instance tag are deliberately distinct. One
definition may be reused by multiple tags and physical drive instances.

## Parameter catalogue coverage

TwinForge provides manual-backed semantics for all 163 parameter numbers
observed in the reference AOI's bulk-read requests. The catalogue records:

- the Rockwell parameter code and group;
- purpose and engineering units;
- ranges, enumerated options, and status flags where documented;
- defaults and display resolution where documented;
- read-only and stop-required constraints; and
- relationships among fault codes and their frequency, current, and DC-bus
  snapshots.

This is complete coverage of the parameters exercised by this particular AOI,
not of every parameter supported by every PowerFlex 525 firmware revision.
The generated
[`corpus_evidence.md`](../../reports/Dev_PF525_Program/corpus_evidence.md)
contains the observed inventory and curated semantics. Potential discrepancies
between the AOI and the manual remain isolated in
[`aoi_qa_issues.md`](../../reports/Dev_PF525_Program/aoi_qa_issues.md) for
manual verification; TwinForge does not silently rewrite the source AOI.

The generated
[`cyclic_io_contract.md`](../../reports/Dev_PF525_Program/cyclic_io_contract.md)
documents the 8-byte drive-to-controller status image and the 4-byte
controller-to-drive command image. It distinguishes configured connection
evidence, captured datatype overlays, and AOI-specific command behavior.

The generated
[`diagnostic_fault_report.md`](../../reports/Dev_PF525_Program/diagnostic_fault_report.md)
separates live drive faults, controller-module faults, communications state,
configured communication-loss behavior, the ten-entry fault-history contract,
and the distinct active-fault reset and history-clear commands.

The generated
[`functional_description.md`](../../reports/Dev_PF525_Program/functional_description.md)
combines command-source modes, run and jog behavior, permissive/interlock
gating, start delay, speed limiting, setpoint tracking, communications,
parameter services, and diagnostic boundaries into one traceable engineering
description.

The generated
[`conversion_readiness.md`](../../reports/Dev_PF525_Program/conversion_readiness.md)
classifies portable logic, datatype and instruction adaptations, target
adapters, manual design review, and hardware validation. It is the staged
implementation checklist for PLCopen/CODESYS conversion while preserving a
separate adapter boundary for future OpenPLC support.

The target-neutral runtime boundary is implemented in
[`runtime/cyclic_io.py`](../../src/twinforge/runtime/cyclic_io.py) and
[`runtime/contracts.py`](../../src/twinforge/runtime/contracts.py). The cyclic
layout is built from the captured `CyclicIOContract`; it is not a second
hard-coded interpretation of the source XML. Tests verify little-endian
packing, signed feedback, bit overlays, preservation of unspecified bytes and
bits, image-size rejection, and parameter request semantics.

Cyclic transport adapters exchange the exact raw images through
`CyclicIOProvider`. Parameter and module operations use separate non-blocking
contracts so converted IEC logic does not depend directly on Logix `MESSAGE`,
`MODULE`, CODESYS device-tree objects, or a future OpenPLC fieldbus API.

The portable command engine is implemented in
[`powerflex525_core.py`](../../src/twinforge/runtime/powerflex525_core.py).
It retains command-source arbitration, level and latched run behavior,
permissive and interlock equations, start delay, command-word construction,
jog selection, speed limiting, and retained state. The engine accepts
normalized status and returns cyclic values; explicit messaging and module
services remain outside it. Its `prescan()` deliberately preserves portable
run and timer state because the captured Prescan routine does not explicitly
write those values. A target may invoke the separate explicit reset only when
the project lifecycle policy requires and documents it.

Two source behaviors are deliberately preserved rather than silently changed:
the commented run-interlock terms tracked by `PF525-QA-020`, and the
program-jog precedence tracked by `PF525-QA-021`.

The portable core can be emitted as executable IEC IR by
[`powerflex525_iec.py`](../../src/twinforge/exporters/powerflex525_iec.py).
The generated
[`PowerFlex525_core_codesys.xml`](../../examples/PLCOpenXML/PowerFlex525_core_codesys.xml)
contains `TF_PowerFlex525_Core`, a calling `PLC_PRG`, and a cyclic `MainTask`.
The function-block body contains no `MESSAGE`, `MODULE`, GSV/SSV, CODESYS
device-tree, or fieldbus API calls.

TwinForge can also package the portable core and normalized CODESYS
EtherNet/IP module binding into one application:

```powershell
uv run python examples/export_powerflex525_codesys_application.py `
  examples/PLCOpenXML/PowerFlex525_codesys_application.xml `
  --device-variable Dev_PF525
```

The project contains both function blocks, one `PLC_PRG`, and one `MainTask`.
It observes the configured `RemoteAdapter_diag` object and performs the
capability-gated single-call reconfiguration handshake. The native device-tree
object and its cyclic channel mappings remain deployment dependencies;
TwinForge does not fabricate them in PLCopen XML.

Multiple physical drives share the same reusable function-block types while
receiving isolated program instances and variables. Supply one `--drive`
argument per configured native CODESYS device:

```powershell
uv run python examples/export_powerflex525_codesys_application.py `
  examples/PLCOpenXML/PowerFlex525_two_drive_codesys_application.xml `
  --drive PF525_01=Dev_PF525_01 `
  --drive PF525_02=Dev_PF525_02
```

`PF525_01` and `PF525_02` are deployment instance names, not inferred process
equipment names. TwinForge emits `TF_PowerFlex525_Core` and
`TF_Codesys_ENIP_ModuleBinding` once, then creates independent core, diagnostic
binding, reconfiguration, command, status, and cyclic-I/O variables for each
drive. Device names and CODESYS symbols must be unique IEC identifiers.

For a reproducible deployment package, validate the checked-in JSON manifest
and generate a self-contained CODESYS bundle:

```powershell
uv run python examples/export_powerflex525_codesys_bundle.py `
  examples/deployment/powerflex525_two_drive.json `
  build/powerflex525_two_drive
```

The bundle contains `manifest.json`, `native-device-template.export`,
`application.xml`, and `IMPORT.md`. Pydantic validates external manifest
syntax, IEC identifiers, unique names, unique addresses, RPI, image sizes, and
connection-path bytes. The exporter then verifies those values against the
native CODESYS fixture before writing anything. Pydantic remains an input
boundary; TwinForge's internal domain model and executable IR remain ordinary
typed dataclasses.

Export 45 remains the verified complete two-drive project baseline. Export 46
contains only the native Ethernet scanner, its generated scanner tasks, and
the two configured device objects. The deployment manifest therefore declares
export 46 as `device_configuration`, enabling the clean two-stage workflow:
import the native template at the top-level device, then select `PLC Logic`
and import the generated PLCopen application. CODESYS creates a second
application whose POUs and `MainTask` must be consolidated into the original
application containing the scanner tasks.

That workflow was manually verified with a fresh CODESYS Control Win V3 x64
project. Importing export 46 created both native devices and the two scanner
tasks without application POUs. Importing the generated PLCopen XML at
`PLC Logic` created `Application_1`; moving its three POUs and `MainTask` into
the original application, deleting the empty imported application, running
Clean All, and building completed successfully.

All generated program inputs start at zero or false. In particular,
non-bypassable permissive/interlock inputs and maximum speed do not default to
an operational state. The imported demonstration therefore cannot produce a
run command until the user deliberately supplies the required status,
command-source, permissive, interlock, availability, speed-limit, and drive
feedback bindings.

CODESYS CAA Device Diagnosis is unrelated source evidence. It belongs only to
the future CODESYS target adapter for observing or controlling the imported
device connection.

The portable behavior of the referenced `Sys_Module` AOI is implemented and
tested separately in
[`sys-module-core.md`](../architecture/sys-module-core.md). It preserves raw
EntryStatus decoding, the shared inhibit/uninhibit edge latch, and explicit
Prescan assignments while keeping GSV/SSV execution behind the target-adapter
boundary.

The CODESYS diagnostic and reconfiguration work is not PowerFlex-specific.
The reusable EtherNet/IP adapter and the separate responsibilities of a
PowerFlex device profile are documented in
[`codesys-ethernetip-module-adapter.md`](../architecture/codesys-ethernetip-module-adapter.md).
The generated
[`sys_module_codesys_equivalence.md`](../../reports/Dev_PF525_Program/sys_module_codesys_equivalence.md)
records the support and semantic-equivalence classification separately.

## CODESYS native visualization evidence

The user-authored native CODESYS export
`reference/PLCopenXML/codesys-native/12_powerflex_visualization.export`
is an interoperability test fixture, not PLCopen XML. TwinForge can inventory
its visualization, controls, geometry, text, IEC variable bindings, Toggle and
InputBox actions, and selected Visualization Manager settings using
[`codesys_native.py`](../../src/twinforge/parsers/codesys_native.py). The
generated
[`codesys_visualization_inventory.md`](../../reports/Dev_PF525_Program/codesys_visualization_inventory.md)
records that evidence.

The native format is a profile-dependent `IArchivable` object graph with
opaque GUIDs and numeric property identifiers. The parser therefore retains
the complete source archive and raw XML for every decoded object. TwinForge
does not yet generate native CODESYS visualization exports: the numeric
property mapping must first be compared with exports from additional CODESYS
profiles and deliberately varied controls.

Friendly native-property decoding is selected through the exact profile
registry in
[`codesys_native_profiles.py`](../../src/twinforge/parsers/codesys_native_profiles.py).
The tested `CODESYS V3.5 SP22 Patch 2` mappings include X, Y, width, height,
text, and the experimentally confirmed centre coordinates. Unknown profiles
remain lossless but undecoded; they never inherit SP22 mappings implicitly.

Parsed evidence is lowered through
[`codesys_visualization.py`](../../src/twinforge/converters/codesys_visualization.py)
into the
[`vendor-neutral visualization model`](../architecture/visualization-model.md).
The model contains portable controls, geometry, bindings, and interactions;
native CODESYS XML and numeric properties remain attached as source
extensions for lossless round-tripping and future profile-specific export.

The controlled procedure and initial export series are defined in
[`CODESYS-visualization-differential-testing.md`](CODESYS-visualization-differential-testing.md).
TwinForge provides
[`diff_codesys_visualizations.py`](../../examples/diff_codesys_visualizations.py)
to produce a semantic and opaque-property report from each baseline/variant
pair.
