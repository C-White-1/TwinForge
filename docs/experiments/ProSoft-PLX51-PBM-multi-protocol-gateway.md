# ProSoft PLX51-PBM multi-protocol gateway evidence

## Purpose

The PLX51-PBM reference bundle is TwinForge's first bounded fixture spanning
EtherNet/IP, PROFIBUS DP, Modbus, and Rockwell AOI evidence. It is suitable for
developing vendor-neutral gateway, endpoint, assembly, and address-mapping
models. It does not yet contain a user configuration export that proves a
specific PROFIBUS-to-Modbus or PROFIBUS-to-EtherNet/IP point mapping.

## Provenance and storage

The files were acquired on 12 August 2026 from the
[ProSoft PLX51-PBM product page](https://www.prosoft-technology.com/Products/Gateways/PLX5x/PROFIBUS-DP-Master-Slave-to-EtherNet-IP-Modbus-TCP-IP-R-or-Modbus-R-Serial-Gateway).
They remain vendor-owned external reference material under
`reference/Gateways/Prosoft/PLX51-PBM/`, which is excluded from Git by the
repository artifact policy. The installers are evidence only and are not
executed by TwinForge tests.

<!-- markdownlint-disable MD013 -->

| File | SHA-256 |
| --- | --- |
| `0135000C146C0100.eds` | `E241B2807BA8F3F2106F281F5D8A7B2FC704972D9CF5B5B8F8D10CB63301DA63` |
| `PSFT10FE.GSD` | `9C1F3B2A259D82706CC8C1C39C37C37C8FE11AD73850702E7F7A4196EA7E397B` |
| `PLX51_PBM_AOI_v1.0.L5X` | `723B91E03F5ECE1A225B8E1DA476FFCE9481C8D7A25485DFA5A71C1D5635CAC2` |
| `PLX51-PBM_Datasheet.pdf` | `AAA6E341404110515E01307FD257FD2FD74274C798ADEF102E624B58B73BAC12` |
| `PLX51-PBM_User_Manual.pdf` | `1D8BB89900DD6BBCE6B673B10D98C395FABD05CCEFCDE9523B21011B85D7600D` |
| `PLX50 Configuration Utility 1.038 Setup.exe` | `AB5E5F5F3F2942644F46192303958032F3E2DE3482138CD7A949EF21623BEEBD` |
| `ProSoft Technology - PLX51 ILX56 HART and Profibus DTM Pack 1.009 Setup.msi` | `8E85430F4EBF82E97D70E9B0E30580D38C211D3E49978896ABE839E9A7121DF2` |
| `Readme.txt` | `74CCD0D48F3B4909265B644D636BADC2DBB674A88B3F284B2DB9CB9AE52E2532` |

<!-- markdownlint-enable MD013 -->

## Confirmed evidence

### EtherNet/IP EDS

The EDS identifies a ProSoft `PLX51-PBM` communications adapter with CIP vendor
ID 309, product type 12, product code 5228, and revision 1.1. It declares four
exclusive-owner Class 1 I/O connections. Their connection paths reference:

| Connection | Configuration | O to T output | T to O input |
| --- | ---: | ---: | ---: |
| 1 | 102 | 133 | 132 |
| 2 | 102 | 135 | 134 |
| 3 | 102 | 137 | 136 |
| 4 | 102 | 139 | 138 |

The assembly declarations retain lexical counts of 4000 for each input and
3968 for each output while referencing the one-byte `Data` parameter. The
connection declarations establish corresponding maximum sizes of 500 and 496
bytes. TwinForge must preserve both EDS forms and defer their unit-level
interpretation to an EDS parser. They must not be treated as configured project
sizes without a configuration export.

### PROFIBUS GSD

The GSD identifies `PLX51-PBM`, revision V1.0, with PROFIBUS ident number
`0x10FE`. It describes a modular PROFIBUS DP slave with up to 40 modules,
244 input bytes, 244 output bytes, and 488 total data bytes. Available module
choices include 1, 2, 4, 8, and 16-byte input or output blocks.

This GSD describes the gateway's PROFIBUS **slave** role. It does not describe
the downstream PROFIBUS devices used while the gateway operates as a master.
Those devices require their own GSD files and a PLX50 configuration project.

### Rockwell AOI

TwinForge parses the AOI without diagnostics. The export contains:

- controller `PLX51_PBM_AOI_Final_v21`;
- 29 controller-defined datatypes;
- AOI `AOIPLX51PBM` revision 1.0;
- 12 parameters, including one module structure and nine `MESSAGE` objects;
- six local `INT` tags; and
- one RLL routine containing nine rungs.

The AOI implements DPV1 acyclic operations and diagnostics: Class 1 read,
write, and alarm; Class 2 initiate, abort, read, and write; global control; and
slave diagnostic requests. It is not, by itself, the cyclic I/O or Modbus
register map.

## Evidence boundaries

The artifacts describe three related but distinct data paths:

1. EtherNet/IP Class 1 cyclic assemblies from the EDS;
2. PROFIBUS DPV1 acyclic services exposed through AOI `MESSAGE` instructions;
3. PROFIBUS-to-Modbus mappings created by the PLX50 Configuration Utility.

TwinForge must not infer one mapping from another. A configuration project or
configuration-generated report is required before individual PROFIBUS points,
assembly offsets, Modbus registers, and AOI/controller tags can be correlated.

## Proposed implementation order

1. Parse EDS identity, assemblies, and connection paths into retained evidence.
2. Parse GSD identity, limits, and selectable module definitions.
3. Model a vendor-neutral gateway with multiple protocol endpoints.
4. Ingest a non-secret PLX50 configuration export or generated report.
5. Correlate configured offsets with AOI structures and controller tags.
6. Add Modbus areas and register mappings only when explicitly evidenced.

The first parser target should be the EDS because TwinForge already models CIP
identity and connections. GSD ingestion should follow as a separate parser;
the two sources should meet only in a later correlation service.
