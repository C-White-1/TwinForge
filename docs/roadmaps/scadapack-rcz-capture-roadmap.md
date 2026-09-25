# SCADAPack `.RCZ` capture roadmap

This turns the [`.RCZ` format investigation](../architecture/scadapack-rcz-format.md)
(six real fixtures characterized, no code written) into an actual TwinForge
capability. Status before this roadmap: investigation only, explicitly
flagged as "nothing here should be read as a commitment to build SCADAPack
support." This roadmap is that commitment, scoped to what the investigation
actually proved, not what it merely observed.

## What the investigation proved (confirmed, not assumed)

- Container navigation is trivial: `.RCZ`/`.STA` are ordinary ZIP files (`PK`
  magic), nested one level. No SCADAPack-specific logic needed for this part.
- `Station.apd`/`Station.apx` embed one or more **raw zlib streams, no
  gzip/zip wrapper** — found reliably by scanning for zlib header bytes, not
  markers. Confirmed across all six fixtures.
- `STATION.CTX` has a fully-decoded, simple UTF-16 framing.
- **On the two newest fixtures' `APPLICATION LIBSET` versions (V15.1,
  V16.20), `STSource` streams decompress to plain XML** —
  `<STExchangeFile><STSource>...</STSource><D1 ...>...</D1></STExchangeFile>`,
  a bare, self-contained fragment (no `fileHeader`/`contentHeader` envelope,
  unlike a real XEF or `.xdb` file — this is an internal serialized artifact
  recovered from inside a compressed blob, not a document Control Expert
  itself would export standalone).
- **On the two oldest fixtures (V11.1, V14.0), the same streams are wrapped
  in a distinct, only partially-decoded .NET `BinaryWriter` string framing.**
  String *boundaries* are confirmed exactly (7-bit length-prefixed UTF-8,
  verified byte-for-byte on four field names across two fixtures). The
  surrounding object-graph *shape* (which decoded values are lengths, flags,
  or the per-statement offset table whose fields `O0`/`k` are understood in
  concept but not confirmed byte-for-byte for this framing) is not solved.
- `.prj`/`.PRJ`'s `.NET BinaryFormatter` blobs are readable via a generic
  regex against `System.UnitySerializationHolder`'s embedded DataContract
  XML, with no real deserializer — proven on two fixtures, 17 and 27
  fragments respectively. This is comm-channel/protocol configuration
  (DNP3/TeleBus addressing), not the RTU's own program logic.
- **Not confirmed at all:** the plain-XML shape of an `FBDExchangeFile`
  stream. Every real FBD sample found so far is on an *old*, binary-framed
  fixture. Checked directly before writing this roadmap — no local fixture
  has a plain-XML FBD stream to test against. Assuming it matches Control
  Expert's `FBDSource`/`networkFBD`/`FFBBlock` grammar would be a guess, not
  evidence, even though the underlying tool family is confirmed shared
  (`Station.apx`'s own XML proves SCADAPack Logic is a rebranded Control
  Expert/Unity Pro build).

## Architecture

A new, independent `parsers/scadapack/` package, following this project's own
established convention (`parsers/control_expert/`, `parsers/l5x/` each own
their capture layer fully — no shared base class to force-fit this into).

Two capture phases, not one, because `Station.apd`/`Station.apx` are not
themselves valid archives or XML — they are proprietary binary shells around
embedded zlib streams:

1. **Archive navigation** (`.RCZ` → `.STA` → members): ordinary recursive ZIP
   walking. Structurally identical in shape to Control Expert's own archive
   handling, but implemented independently per the established per-format
   convention above — not imported from `parsers/control_expert/capture.py`,
   which is intentionally scoped to that format.
2. **zlib stream extraction**, applied to `Station.apd`/`Station.apx`
   specifically (and any bare-stream member like `.xma`): scan for zlib
   header bytes, decompress each candidate, classify by the decompressed
   content's own type marker (`STExchangeFile`, `FBDExchangeFile`,
   `TABExchangeFile`, a `unity.*` settings key, or unrecognized). Each
   resulting stream becomes its own captured member, byte-preserved like
   every other TwinForge capture layer, never silently dropped even when
   unparsed.

Model choice: a plain-XML `STExchangeFile` stream's `STSource` element is the
same concept as a DFB's own `STSource` body — reuse `StructuredTextLine`
directly, not a new SCADAPack-specific text-routine type. What container it
came from (a project's own program, a DFB's `FBProgram`, or a decompressed
SCADAPack stream) doesn't change what a line of Structured Text *is*.

## Milestone 1: container + plain-XML `STSource` only

- [x] `parsers/scadapack/capture.py`: recursive ZIP walk (`.RCZ`/`.STA`),
  zlib-stream extraction and classification for `Station.apd`/`Station.apx`
  members, full byte preservation and diagnostics for every stream whether
  understood or not
- [x] Parse a plain-XML `STExchangeFile`/`STSource` stream into
  `StructuredTextLine`s, gated strictly on detecting the `<?xml` declaration
  (never attempted against the binary-framed shape — retained as evidence,
  diagnosed `unsupported_binary_framed_stream`, not guessed at). Also
  gracefully handles a UTF-8 BOM before `<?xml` (real evidence: `.PRJ`
  files carry one; a naive prefix check without stripping it would have
  wrongly classified every `.prj`/`.PRJ` as opaque)
- [x] Retain the `<D1>` per-statement offset table as evidence
  (`source_extensions`), not interpreted — `O0`/`k` are understood in
  concept only, `p`/`p1` not even that
- [x] `STATION.CTX` decoded into plain key/value metadata (RTU model,
  `APPLICATION LIBSET` version, `STU COMPATIBILITY LEVEL`) — verified
  byte-for-byte against real fixture bytes before coding, not just against
  the investigation doc's prose summary
- [x] Every non-`STExchangeFile` stream (settings tables, binary-framed
  content, unrecognized) explicitly retained and diagnosed, never silently
  dropped
- [x] Tests against synthetic fixtures (14 tests across
  `test_scadapack_capture.py` and `test_scadapack_station.py`) plus a manual
  (uncommitted) run against the real local corpus for confidence --
  including the first genuinely real-world-scale fixture
  (`LiftStationLib.RCZ`, 8 ST streams, zero diagnostics) alongside the
  original small/trivial ones

## Explicit non-goals for Milestone 1

- **FBD content of any kind.** No plain-XML shape confirmed yet; the old
  binary-framed shape is not solved. Any FBD stream found is retained and
  diagnosed unsupported, not parsed.
- **The binary-framed `STSource` shape** (V11.1/V14.0). String boundaries
  are solved; the object-graph shape is not. Guessing at it would produce
  plausible-looking but unverifiable ST source — worse than an honest gap.
- **`.prj`/`.PRJ` DTM/comm-channel parsing.** Real, proven-readable content,
  but a materially different concern (protocol/addressing config, not
  program logic) — its own milestone once Milestone 1's program-logic path
  is solid.
- **`TA.xma`/`TABExchangeFile`** (animation tables/watch lists). Bare,
  unframed zlib — likely easy once Milestone 1's classification step
  exists, but not attempted until it does.
- **A `Controller`/`Program`/full-project model.** A `.RCZ`'s equivalent of
  a "project" is a genuinely open question (does one RTU's captured content
  map to one `Controller`, given DNP3/comm config lives in a totally
  separate file from program logic?) — not decided here, deferred until
  there is real ST content to hang a decision on.

## Milestone 2 and beyond (not scoped in detail yet)

- FBD content, once a plain-XML sample is found or the binary-framed shape
  is solved (whichever comes first)
- `.prj` DTM/comm-channel mapping into the model (likely `LibraryInterface`-
  adjacent, not `Controller` hardware — an RCZ's own comm DTM is protocol
  config, not a rack/module)
- The binary-framed older-version `STSource` shape, if a fixture strictly
  between V14.0 and V15.1 ever turns up to narrow the search
- CLI surface (`twinforge scadapack inspect <file>`), once there is a real
  parsed model worth inspecting

## Verification

Every real fixture in the local (gitignored) `reference/SCADAPack/` corpus:
confirm plain-XML `STSource` streams parse cleanly and binary-framed ones are
diagnosed, not guessed at. No fixture leaves this repository — verification
stays local-only per the artifact policy already established for this
format.
