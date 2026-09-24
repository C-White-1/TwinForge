# SCADAPack RTU `.RCZ` project format — investigation notes

Status: **investigation only.** No capture, parser or model support exists in
TwinForge for this format. This document records what has been directly
observed in one sample file so the next session does not need to rediscover
it. Nothing here should be read as a commitment to build SCADAPack support.

## Provenance

`reference/SCADAPack/sp470_v04.RCZ` (104,430 bytes) was supplied locally by
the user, not downloaded by TwinForge. Per the user (2026-09-24), it is a
small Schneider Electric example project demonstrating DNP3 setup on a
SCADAPack x70 RTU (SP470 hardware) — a vendor tutorial file, not a
representative real-world project. Its small scope (three lines of
Structured Text, no populated ladder/SFC/DFB content found so far) should be
read in that light, not as evidence of the format's typical size or
complexity. Per [the artifact policy](../artifact-policy.md), this file
stays local-only under the ignored `reference/` tree.

## Container structure (confirmed)

```
sp470_v04.RCZ                      ZIP
├── sp470_v04.prj                  FDT/DTM XML (see below)
├── sp470_v04.STA                  nested ZIP
│   ├── STATION.CTX                custom UTF-16 framed text (fully decoded)
│   ├── BinAppli/Station.apx       proprietary binary, magic "APX\0"
│   ├── BinAppli/Station.apd       proprietary binary, magic "APD\0"
│   └── ThirdParty/                empty in this sample
└── version.txt                    plain text: "RemoteConnect Package
                                    Version: R2.4", "SCADAPack x70 Version:
                                    3.7.2177"
```

`sp470_v04.prj` is an `<FdtDtmProject>` XML document (IEC 62453 FDT/DTM)
whose project-, DTM- and TopologyRecord-level `<EngineeringData>` elements
hold base64-encoded .NET `BinaryFormatter` blobs. These have not been
deserialized — only recognized by their `AAEAAAD/////AQAAAAAA...` header
pattern and embedded readable .NET type/assembly name strings.

`STATION.CTX` uses a simple, fully-decoded repeating frame:
`\xff\xfe\xff<length-byte><UTF-16LE text>`, alternating field-name/value
pairs. It yielded 35 clean fields, including `STU COMPATIBILITY LEVEL: 102`
and `APPLICATION LIBSET: V14.0`.

## `Station.apx` and `Station.apd`: raw zlib streams inside a proprietary shell

Both files are otherwise undocumented binary containers, but each embeds one
or more **raw zlib streams with no gzip/zip wrapper**. They were located by
scanning for zlib header bytes (`0x78` followed by `0x01`, `0x5e`, `0x9c` or
`0xda`) and attempting `zlib.decompress` from each candidate offset — not by
relying on marker text. (`Station.apx` happens to also contain a literal
`"ZLIB"` string shortly before its stream; `Station.apd`'s streams do not, so
the byte-scan approach is the reliable one.)

**`Station.apx`** (29,394 bytes) contains one zlib stream, at offset 17,754,
consuming 6,772 bytes and decompressing to 31,019 bytes of plain Unity
Pro/Control-Expert-schema XML (`unity.xsd`, `<crypted Level="255">` wrapping
`<PACKAGE>` and `<PROJECT>`). This is direct evidence that **SCADAPack x70
Logic is a rebranded Control Expert / Unity Pro 14.0 build**:

- `<UnityPackage><ProductName value="UnitySoControl"/>`
- `<DisplayName value="SCADAPack x70 Logic"/>`
- `<ProductVersion value="14.0"/>`
- Converter DLLs declaring native `XEF`/`ZEF`/`FEF` support
  (`STMUI.DLL`, `CPL7MANAGER.DLL`)

That `<PROJECT>` section is essentially empty in this sample (only
placeholder `<ProjectFunctionalities>` comments) — it is application/editor
feature configuration, not the user's program.

After that XML stream ends (absolute offset 24,526), the remaining 4,868
bytes of `Station.apx` hold a separate, still-unparsed binary-framed table
containing:

- System fault/diagnostic labels paired with system bits/words, e.g.
  `"Local I/O fault"` / `%S119`, `"Ethernet IO fault"` / `%S117`,
  `"Watchdog overflow"` / `%S11` — standard Control Expert system-word
  descriptions, not project-specific.
- The RTU's physical I/O tag names for this SP470 hardware profile:
  `PIO_SP470_AI1..4`, `PIO_SP470_DI1..4`, `PIO_SP470_DO1..2`,
  `PIO_SP470_CI1..4` (each with a paired `_Freq` variant).

**`Station.apd`** (5,165 bytes) contains **four** separate raw zlib streams
(offsets 184, 2608, 2879, 4130). Three decompress to Unity Pro
settings/preference key tables (e.g. `unity.IOScanningMode`,
`unity.SaveOnDownloadSTU`, `unity.dataDictionary*`) — editor state, not
program logic. The stream at offset 184 (381 bytes decompressed) is
different: inside its own short length-prefixed binary frame, labeled
`STExchangeFile` / `STSource`, it contains an embedded XML declaration
followed directly by real user Structured Text source:

```
AI1_High_Res.Value := PIO_SP470_AI1.VALUE;
AI1_Med_Res.Value := PIO_SP470_AI1.VALUE;
AI1_Low_Res.Value := PIO_SP470_AI1.VALUE;
```

This ties directly back to the `PIO_SP470_AI1` tag found in the `Station.apx`
I/O table, confirming this is genuine project logic (an analog-input scaling
rung), not vendor boilerplate.

## Open questions

- The binary framing used inside `Station.apx`/`Station.apd` (short
  length-prefixed strings/fields, distinct from `STATION.CTX`'s UTF-16
  framing) has only been sampled ad hoc — there is no general parser or
  documented grammar for it. A single small example file is not enough to
  generalize the framing rules; more samples would be needed before this
  could be approached in a specification-driven way per
  [AGENTS.md](../../AGENTS.md).
- Whether this sample's minimal content (one ST rung, no populated
  ladder/SFC networks found) reflects the format's normal ceiling or simply
  this tutorial file's narrow scope is unknown.
- The `.prj` file's per-DTM/TopologyRecord `.NET BinaryFormatter` blobs have
  not been deserialized; they may hold DNP3 channel/device configuration
  relevant to the RTU's stated purpose (a DNP3 setup example) but were not
  investigated.
- No relationship has been established yet between this format and
  TwinForge's existing [Control Expert XEF/ZEF capture
  work](control-expert-exchange-capture.md) beyond the shared Unity Pro
  lineage confirmed above — SCADAPack's `.RCZ`/`.STA` container is a
  different on-disk shape from a standalone XEF/ZEF export, not just a
  renamed one.
