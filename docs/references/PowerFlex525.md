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

CODESYS CAA Device Diagnosis is unrelated source evidence. It belongs only to
the future CODESYS target adapter for observing or controlling the imported
device connection.
