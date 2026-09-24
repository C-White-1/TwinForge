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

## Second fixture: `leadLagPumpCtrl_v02.RCZ` (2026-09-24), a real application

`reference/SCADAPack/RC_ Lead Lag Pump_Project Files.zip` (114,379 bytes,
containing one file, `leadLagPumpCtrl_v02.RCZ`) was supplied locally by the
user, not downloaded by TwinForge; no license stated; kept local-only under
the ignored `reference/` tree per the artifact policy. Unlike `sp470_v04`,
this is a genuine small real-world application (alternating lead/lag pump
control from tank-level thresholds), not a vendor tutorial, and it answers
one of the open questions below directly: the first fixture's minimal
content was that file's own narrow scope, not a ceiling on what this format
can hold.

Same container shape confirmed again (`.RCZ` → `.PRJ` + `.STA` →
`Station.apd`/`Station.apx` + `STATION.CTX`), from a different hardware
generation and tool version than the first fixture — direct evidence the
structure generalizes, not a one-off: `PROCESSOR=SCADAPack57x` (not x70),
`APPLICATION LIBSET=V11.1` (not V14.0), `STU COMPATIBILITY LEVEL=93` (not
102), dated 2019-03-17, talking to a real Modbus/TCP address
(`PLC ADDRESS=10.2.3.4:504`).

One new top-level member this time: `TA.xma` (328 bytes) inside the `.STA`
zip, alongside `Station.apd`/`Station.apx`. It is a **raw zlib stream with
no framing at all** (starts directly with a `0x78 0xda` header, no
`STATION.CTX`-style or length-prefixed wrapper around it) — decompresses
straight to a `TABExchangeFile` (an animation-table / watch-window export)
listing real tag references: `TankLevel`, `PumpLag.VALUE`,
`PumpLead.VALUE`, `TankLevel.VALUE_ENG`.

`Station.apd` this time holds **six** raw zlib streams (found the same way,
by scanning for zlib header bytes, not markers), not four. Three are
recognizable settings/preference tables as before. The other three are real
program content, and together they tell a coherent, complete story:

- One `STExchangeFile`/`STSource` stream, complete and self-contained (not
  truncated the way the first fixture's felt on its own): four fully
  commented lines of Structured Text copying tank-level threshold states
  into lead/lag control flags:

  ```st
  (* copy Tank Level limit states to lead / lag control variables *)
  LagPumpOn := TankLevel.H2_STATE;    (* 90 *)
  LeadPumpOn := TankLevel.H1_STATE;   (* 80 *)
  LagPumpOff := TankLevel.L1_STATE;   (* 30 *)
  LeadPumpOff := TankLevel.L2_STATE;  (* 20 *)
  ```

  (the numeric comments read naturally as tank-level percentage setpoints).
- Two `FBDExchangeFile` streams, a matched pair — one driving the lead pump,
  one the lag pump, same structure, different tags. Each has two `MOVE`
  blocks and one `AND` block (`EN`/`IN`/`ENO`/`OUT` and `EN`/`IN1`/`IN2`/
  `ENO`/`OUT` pins, matching the pin-naming convention already established
  from the Control Expert corpus), moving `LeadPumpOn`/`LeadPumpOff` (or the
  `Lag` equivalents) into `PumpLead.VALUE`/`PumpLag.VALUE`, each block
  carrying a real author comment: *"Control lead pump ON or OFF when limit
  is exceeded."* and *"When neither limit is active, jump to end of
  program."*

`Station.apx`'s main zlib stream (still one stream, still marked by a
literal `ZLIB` string beforehand) decompresses to the same
`<PACKAGE>`/`<PROJECT>` shape as the first fixture, and its `<PROJECT>`
section is *again* just the placeholder `<ProjectFunctionalities>` comment
block, empty of real content. Confirmed pattern, now 2/2: `Station.apx`'s
own XML stream is always editor/feature configuration; the real program
(ST/FBD sections) lives exclusively in `Station.apd`'s separate streams.

## The `.PRJ`/`.prj` `.NET BinaryFormatter` blobs are not actually opaque

Previously an open question (see below, before this pass): whether the
`.prj`/`.PRJ` file's per-DTM `EngineeringData` and `InstanceDataRecord`
values — base64 .NET `BinaryFormatter` blobs — held anything readable.
They do, and reliably: `BinaryFormatter` here uses
`System.UnitySerializationHolder`, a .NET remoting surrogate that embeds
the *actual* object as a complete, self-contained WCF DataContract XML
document (namespace `http://schemas.datacontract.org/2004/07/Fdt...`)
inside the blob, after a short type-table preamble. No real
`BinaryFormatter` deserializer, and no knowledge of the .NET type graph,
is needed to reach it: a single generic regex —
`<([A-Za-z][\w.]*)(?: [^>]*)?>.*?</\1>` (DOTALL) against the raw
(non-UTF-16) bytes — reliably pulls out every complete embedded XML
fragment, root tag name and all. Confirmed on `leadLagPumpCtrl_v02.RCZ`:
17 distinct, well-formed fragments extracted this way from 5 top-level
`EngineeringData` blobs and their nested `InstanceDataRecord` values, with
zero false starts.

What they contained, for this fixture: both DTMs in the project
(`DTMDisplayName` read the same way as before, via `CustomAttributes`) are
DNP3-related — "PC Communication Settings -DNP3 CommDTM" (the parent/PC
comm channel) and "SCADAPack x70 Controller Settings -DeviceDTM" (the
child field device) — each declaring the same four supported protocol
variants (`DeviceTypeInfo/BusCategories`: DNP3 Serial Line, DNP3 TCP,
DNP3 UDP, DNP3 USB, each with a stable `ProtocolId` GUID). Three
`AddressInfo` fragments per DTM give the full connection parameters for
each variant (DNP3 TCP: target address `1`, `127.0.0.1:8080`; DNP3
Serial: target address `0`; DNP3 USB: `LocalConnection=true`), and an
`ActiveProtocol` fragment names which one is actually selected for this
project — DNP3 USB here, a local/direct connection, distinct from (and
not to be confused with) `STATION.CTX`'s own separate `PLC ADDRESS`
(the RemoteConnect IDE's own download/monitor connection, `10.2.3.4:504`,
Modbus TCP) — two independent connection configurations coexist in one
project: the IDE's own PLC link, and this DNP3 CommDTM's own test/runtime
link. A `PersistentData`/`ChannelTopology` fragment on the parent DTM
confirms the FDT device-tree parent/child relationship directly
(`AddedChildDtms` naming the child DTM's GUID) — the comm DTM is the
channel, the device DTM hangs off it, exactly the standard FDT/DTM model
(IEC 62453).

This generalizes past this one fixture: the technique needs nothing
SCADAPack-specific (no schema, no field offsets), only "there is
`System.UnitySerializationHolder`-wrapped data somewhere in this blob" —
which the leading `System.UnitySerializationHolder` type-name string
itself confirms cheaply before even attempting extraction.

Immediately confirmed by revisiting the *first* fixture's `sp470_v04.prj`
with the same method: 27 fragments this time (a richer project — its comm
DTM, plainly named "SCADAPack CommDTM", supports `TeleBus` protocol
variants alongside DNP3, not present in the second fixture at all). Its
`ActiveProtocol`/`BusCategory` fragment names the active protocol as
**DNP3 TCP**, with a real configured `AddressInfo` target of
`172.16.1.200:20000` — a concrete, deliberately-set device address (not a
`127.0.0.1` placeholder), not previously surfaced by the STATION.CTX-only
reading this file first got. Directly confirms, at the protocol-config
level, the user's own description of that fixture as a DNP3 setup example.

## `Station.apd`/`Station.apx`'s own binary framing: not a mystery format

The framing wrapping each decompressed zlib stream's content
(`STExchangeFile`/`STSource`, `FBDExchangeFile`, the `unity.*` settings
tables) is not a proprietary, undocumented scheme either — it is **standard
.NET `BinaryWriter`/`BinaryReader` primitive string encoding**: a `string`
is written as a 7-bit-encoded length prefix (`.NET`'s `Write7BitEncodedInt`
— each byte's top bit means "more bytes follow", low 7 bits contribute to
the value) followed directly by that many UTF-8 bytes, no null terminator,
no fixed width. Confirmed exactly, byte-for-byte, on three independent
field names across both fixtures: the byte before `"STExchangeFile"`
(14 chars) is `0x0e`; before `"STSource"` (8 chars) is `0x08`; before
`"FBDExchangeFile"` (15 chars) is `0x0f`; before
`"unity.variableNotUsed"` (21 chars) is `0x15`. A greedy walk of the full
ST stream applying this rule recovers the entire comment and code text
correctly, string boundary by string boundary, not just as one long
printable run — including short strings a plain "run of 4+ printable
bytes" scan would have split incorrectly or missed (single-character
fields, `"0"`, `"1"`, etc., in what looks like a trailing position/offset
table after the real source text).

This means the fixed preamble bytes before the first real string in every
stream (7-byte magic `\xe5\xe3\xd2\x9e\x02\x00\x00`, identical across both
fixtures' `ST`/`FBD` streams, then a short run of what are very likely
further 7-bit-encoded lengths/counts and raw primitive fields such as
`Int32`/`Boolean`) is a **decodable .NET object-graph serialization**, not
noise — just not yet fully mapped field-by-field without the original
.NET type definitions. What remains genuinely unknown is the *shape* of
that object graph (field order, which values are lengths vs. flags vs.
counts) — the string-encoding rule alone does not hand over the whole
grammar, and two fixtures sharing the same tool version's serialization
layout is not enough evidence to assert the general schema with
confidence.

Applying the confirmed string-decoding rule precisely (not the earlier
ad hoc printable-run scan) to the bytes right after each `ST` stream's
real source text gives, as a sequence of decoded string *values* (still
of unknown meaning — recorded here as raw fact, not interpreted):

- Fixture 1 (`sp470_v04`, 3-line source): `5, 8, 10, 10, 10, 20, 0, 20,
  28, 30, 38, 1, 1, 1, 1, 2, 3`
- Fixture 2 (`leadLagPumpCtrl_v02`, 6-line source incl. comment/blank):
  `6, 8, 10, 10, 10, 10, 20, 0, 38, 60, 88, b0, d8, 1, 1, 1, 1, 3, 4, 5, 6`

Both fixtures' first value equals their own source's line count exactly
(3 real code lines read as `5` is a loose fit; 6 total lines — comment,
blank, 4 code — matches `6` exactly), and several later values
(`20, 28, 30, 38` / `38, 60, 88, b0, d8`) read as ascending hex byte
offsets with a roughly constant stride, suggestive of a per-line offset
table — but this is an unconfirmed *hypothesis* from two data points, not
a claim about what the field is. Recorded as raw decoded values precisely
so a future pass (or a third fixture) can test hypotheses against them
without redoing this extraction.

## A real third+ sample, and an official (non-reverse-engineered) path

Searching externally for another real `.RCZ`, following the same
methodology that has repeatedly found real Control Expert fixtures this
project already relies on, found `apexsotjo-blip/remoteconnect-mcp` (no
license declared, kept local-only, not committed) — an MCP server that
automates SCADAPack RemoteConnect/Control Expert through the vendor's own
COM API, not by parsing these formats from scratch. Two things from it are
directly useful here, for different reasons.

**`src/remoteconnect_mcp/logic_archive_bridge.py`** confirms an *official*
mechanism exists for materializing an `.STA` archive's `BinAppli/
Station.apx`/`Station.apd` payload into a full project: it calls into
Schneider's own API (recorded in its own result dict as
`"method": "UDE OpenAPX"`), not a custom parser -- and that call requires
the real Control Expert/RemoteConnect installation to be present
(`"headless": true` there refers to no UI automation needed, not to
running without the vendor software at all). This calibrates what TwinForge's
own from-scratch, offline extraction (zlib streams + .NET string decoding,
documented above) is actually competing with: not a published spec, but a
vendor API that needs the real software installed -- which is exactly the
gap offline capture is for.

**`examples/comprehensive_demo/RemoteConnect_All_Objects_Demo.stu`** (and
its sibling `.prj`) is a genuine third real fixture, and a richer one: a
"RemoteConnect comprehensive object and protocol-register demonstration"
(`props.xml`: `ProductVersion=UnitySoControl 16.20`, newer than either
prior fixture's 14.0/11.1), deliberately covering Modbus and DNP3 point
types together with advanced DDT object families -- real ST source
assigning through `DEMO_MB_COIL`, `DEMO_MB_DISCRETE`, `DEMO_MB_INPUT_DINT`,
`DEMO_MB_HOLD_REAL` (Modbus scanner/register rows) and `DEMO_DNP_DO`,
`DEMO_DNP_DI`, `DEMO_DNP_AO`, `DEMO_DNP_AI`, `DEMO_DNP_COUNTER` (all five
DNP3 point classes) alongside `DEMO_ANALOG_INT`/`UINT` and
`DEMO_ADV_DIGITAL`/`DEMO_ADV_ANALOG` (with both `.VALUE_ENG` and
`.VALUE_RAW` members) -- real, concrete evidence of SCADAPack's own
per-protocol tag/DDT vocabulary, useful well beyond this specific
byte-framing question.

Also `.STU` (not `.RCZ`) confirmed structurally exactly as the
`jarocki/100daysOfYaraForOT` write-up described (see below): the same
`STATION.CTX`/`BinAppli/Station.apx`/`Station.apd` core, plus `props.xml`
and several `.db` files (`VariableManager.db`, `TypeManager.ODB`,
`XRefManager.db`, `SLM.db`, etc.) that `.RCZ`/`.STA` do not carry -- `.STU`
is the richer, full-project container; `.RCZ`'s `.STA` member is the
lighter one, both sharing the same `BinAppli` core.

**One real, honestly-flagged discrepancy, not smoothed over:** this
fixture's own `STExchangeFile`/`STSource` stream does *not* use the
length-prefixed `.NET` binary framing confirmed above -- it decompresses
directly to plain XML (`<?xml version="1.0" standalone="yes"?>
<STExchangeFile><STSource>...`), no `\xe5\xe3\xd2\x9e...` magic at all.
The *other* streams in this exact same file (`Station.apd`'s settings
tables) *do* still show that magic and the confirmed length-prefix rule
(`"unity.variableNotUsed"` still preceded by `0x15`=21, exact). Since this
demo project was built programmatically through `remoteconnect-mcp`'s own
tools (`tools/bigtest/07_build.py` etc.), not authored interactively, the
likeliest explanation is that this is how *that tool's write path*
produces `STSource` content specifically, not a disproof of the binary
framing found in the two interactively-authored fixtures -- but this is
not confirmed either way, and is recorded as an open discrepancy rather
than resolved in either direction.

## Open questions

- Resolved by the second fixture: whether minimal content in the first
  sample reflected the format's ceiling or just that file's narrow scope.
  It was the latter — real applications hold real, multi-section ST/FBD
  program logic with genuine authored comments.
- Resolved by the second fixture (see above): whether the `.prj`/`.PRJ`
  file's `.NET BinaryFormatter` blobs could be read at all without a real
  deserializer. They can, reliably, via the embedded DataContract XML
  fragments.
- Partially resolved: the string-encoding rule for `Station.apx`/
  `Station.apd`'s own binary framing (distinct from `STATION.CTX`'s UTF-16
  framing, and distinct again from `TA.xma`'s bare unframed zlib stream) is
  now known and confirmed on a *third*, newer-version (`16.20`) fixture too
  (see above) — but the surrounding object-graph structure (field order,
  non-string primitive values, the trailing numeric table's meaning) is
  still not. More samples, especially ones confirmed interactively
  authored rather than tool-generated, would help before this could be
  approached in a specification-driven way per
  [AGENTS.md](../../AGENTS.md).
- New, not yet resolved: the third fixture's own `STSource` stream uses
  plain XML instead of the confirmed binary framing, while every other
  stream in that same file (including another `unity.*` settings table)
  still uses the framing correctly. Likeliest explanation recorded above
  (that fixture's `STSource` content was written by an automation tool's
  own build path, not the interactive editor) is a hypothesis, not a
  confirmed fact — an interactively-authored fixture on the same tool
  version would settle it either way.
- Both fixtures' `TopologyRecord`-level blobs (as opposed to the
  `DTM`-level ones covered above, which is where all 17+27 DataContract
  XML fragments came from) have been checked and yield no fragments at all
  — they appear to be pure tree-position/linkage data (GUID references),
  not further readable content, but this hasn't been confirmed beyond "the
  generic extraction found nothing."
- No relationship has been established yet between this format and
  TwinForge's existing [Control Expert XEF/ZEF capture
  work](control-expert-exchange-capture.md) beyond the shared Unity Pro
  lineage confirmed above — SCADAPack's `.RCZ`/`.STA` container is a
  different on-disk shape from a standalone XEF/ZEF export, not just a
  renamed one.
