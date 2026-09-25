# SCADAPack `.RCZ` capture: development checkpoint journal

This is the dated history of implementation checkpoints for the SCADAPack
RTU `.RCZ`/`.STA` capture work: what was measured, what real corpus
evidence justified each change, and exact test/lint/type-check results at
the time. It is a development log, not a plan.

- Delivery status and what's next: the
  [SCADAPack roadmap](../roadmaps/scadapack-rcz-capture-roadmap.md).
- Observed structures and byte-level evidence: the
  [format investigation](../architecture/scadapack-rcz-format.md).

Entries are in chronological order (oldest first) and are never rewritten
after the fact; a later entry may supersede or withdraw an earlier one, but
the earlier entry stays as the historical record.

Milestone 1 checkpoint (2026-09-25): shipped `parsers/scadapack/` (`capture.py`,
`evidence.py`, `station.py`), the first real code for this format after a
prior investigation-only session. Scope, deliberately narrow: container
navigation, zlib stream extraction/classification, and plain-XML `STSource`
parsing only -- exactly what six real fixtures had actually proven, not what
they merely suggested. Independent package, not folded into
`parsers/control_expert/`, per this project's own established convention
(`parsers/l5x/` also owns its capture layer fully).

Two real, evidence-driven fixes made during implementation, not assumed
correct from the investigation doc's prose:

- **`STATION.CTX`'s framing was verified against real bytes before coding**,
  not trusted from the earlier summary: `\xff\xfe\xff<1-byte char
  count><UTF-16LE text>`, alternating name/value pairs. Matched exactly.
- **A UTF-8 BOM before `<?xml` broke the naive prefix check.** Every real
  `.prj`/`.PRJ` file (confirmed via direct byte inspection of
  `sp470_v04.RCZ`) starts `\xef\xbb\xbf<?xml ...`; the first version of the
  XML-detection check (`data.lstrip()[:5] == b"<?xml"`) missed this and
  classified every `.prj` as opaque. Fixed by stripping the BOM before the
  check, in both the top-level and zlib-stream code paths.

Model choice: a plain-XML `STExchangeFile`/`STSource` stream maps to an
ordinary `Routine`/`StructuredTextLine` -- the same model Control Expert's
own ST bodies already use. What container the source came from (a project's
own program, a DFB's `FBProgram`, or a decompressed SCADAPack stream)
doesn't change what a line of Structured Text is, so no new
SCADAPack-specific text-routine type was added. `Routine.name` carries the
stream's own capture-layer identity (`stream[N]@0xOFFSET`) since there is no
better name evidence -- SCADAPack's `STExchangeFile` streams carry no
section-name attribute the way Control Expert's `program`/`identProgram`
does.

Explicit non-goals held to, not silently expanded: FBD content (no
plain-XML sample exists in the local corpus to test against -- checked
directly before writing the roadmap, not assumed), the binary-framed
older-version `STSource` shape (string boundaries solved, object-graph shape
is not), and `.prj` DTM/comm-channel mapping (recognized and retained as
generic XML, not interpreted).

Verified against the real corpus, not just synthetic fixtures: the newest
real fixture on hand (`RTU_Demo_Proj_SNMP (v2).RCZ`, V15.1) round-trips
cleanly end to end -- 35 `STATION.CTX` fields decoded, one ST routine
resolved with the exact source text already confirmed by hand in an earlier
session, zero diagnostics. The oldest fixture (`sp470_v04.RCZ`, V14.0)
correctly resolves zero routines with an honest
`no_structured_text_found` diagnostic, not a guess. `LiftStationLib.RCZ` --
the first genuinely real-world-scale fixture found so far -- resolves 8
independent ST routines (75 to 350 lines each) with zero diagnostics,
confirming Milestone 1 holds up on real production-scale content, not just
small demos. 14 new synthetic tests (`test_scadapack_capture.py`,
`test_scadapack_station.py`). 1526 tests pass project-wide; Ruff and
Pyright pass.

Pyright-scope fix, same day: CI runs bare `pyright` (repo-wide, `tests/`
included); local verification had only run `pyright src`, missing that
`CapturedArtifact.section` is `Optional` and one test accessed
`.ordered_children` on it without narrowing first. Fixed; re-verified
against the exact CI command set (`ruff check src tests examples`, bare
`pyright`, bare `pytest`) going forward, not a `src`-only subset.

Milestone 2 checkpoint (2026-09-25, same day): shipped `.prj`
`FdtDtmProject` -> `DeviceTypeManager` mapping
(`model/fdt_dtm.py`, `parsers/scadapack/dtm.py`). Originally scoped in the
roadmap as "likely `LibraryInterface`-adjacent" -- wrong on investigation,
before any code was written: `CommunicationInterface`/`Connection` are
Rockwell/CIP-shaped (packet intervals, `unicast`, CIP object/instance/
attribute services) and none of it applies to DNP3/TeleBus protocol-
variant-with-one-active-selection data, so a small new model
(`DeviceTypeManager`/`ProtocolVariant`/`ConfiguredProtocolAddress`) was
added instead of forcing a fit.

Re-reading the real `.prj` XML tree directly (not just trusting the
existing investigation doc's byte-level summary) turned up a much more
structured signal than expected: each `InstanceDataRecord`'s own `Key`
attribute names its content type and, for protocol records, the exact
protocol GUID (`AddressInfo-<guid>`, `ActiveProtocol-<guid>`) -- no need to
blind-scan raw bytes for embedded tags the way the original investigation
did. One genuinely tricky real case, caught by testing against
`leadLagPumpCtrl_v02.RCZ` specifically rather than only synthetic
fixtures: a protocol's catalog name and its configured address can live on
*different* DTMs (the comm DTM declares the catalog, the device DTM holds
the address), cross-referenced only by the shared protocol GUID -- fixed
with a two-pass resolution (collect every DTM's declared protocol names
project-wide before finalizing any DTM's configured list).

Verified against every real fixture with a `.prj`: `sp470_v04.RCZ`
reproduces its documented real DNP3-TCP target (`172.16.1.200:20000`)
exactly; `leadLagPumpCtrl_v02.RCZ` reproduces its documented active
DNP3-USB-local selection exactly, now with the previously-unresolved
inactive variants' own names filled in from the other DTM's catalog; the
two newer fixtures (`RTU_Demo_Proj_SNMP (v2).RCZ`, `LiftStationLib.RCZ`)
resolve cleanly with zero new diagnostics, the latter despite a 2.9MB
`.PRJ` (81ms capture, 6ms mapping -- no performance concern). 6 new
synthetic tests (`test_scadapack_dtm.py`). 1532 tests pass project-wide;
Ruff and Pyright pass.

Explicit non-goals held to: the deeper per-protocol settings groups
(`Dnp3LayerSettingsControlGroup`, `Modbus Settings`, ...) are real,
readable-looking `InstanceDataRecord` content but not decoded; the DTM
parent/child tree relationship remains unconfirmed (the child's GUID
doesn't appear as a readable string in the parent's `ChildList` record --
checked directly, not assumed; likely raw binary GUID form, not text).

CLI surface checkpoint, same day: `twinforge scadapack inspect <file>`
(`cli/scadapack.py`), mirroring `control-expert inspect`'s shape (text and
JSON, station properties + routines + `DeviceTypeManager`s + diagnostics).
Success is "found at least one of station properties, routines, or DTMs";
a fully-empty result is a clean CLI failure, not a silent success with
nothing to show. Verified through the actual CLI entry point against the
real corpus: `sp470_v04.RCZ` prints its active `DNP3 TCP ->
172.16.1.200:20000` line correctly, and the newer SNMP fixture prints its
one resolved ST routine and active `DNP3 USB` selection correctly. 4 new
CLI tests. 1536 tests pass project-wide; Ruff and Pyright pass.
