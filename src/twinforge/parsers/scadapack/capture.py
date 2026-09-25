"""Bounded SCADAPack `.RCZ`/`.STA` archive and zlib-stream inspection.

No filesystem extraction, no model conversion. Unreadable or unrecognized
content retains its identity and an explicit diagnostic rather than being
silently dropped -- the same discipline `parsers/control_expert/capture.py`
follows, implemented independently per this project's own established
convention (each vendor format owns its capture layer; see also
`parsers/l5x/capture.py`).

Scope is exactly Milestone 1 of
docs/roadmaps/scadapack-rcz-capture-roadmap.md, built on
docs/architecture/scadapack-rcz-format.md's investigation:

- `.RCZ`/`.STA` are ordinary ZIP archives (confirmed: `PK` magic), walked
  recursively like any other archive.
- `STATION.CTX` uses a simple, fully-decoded repeating frame:
  `\xff\xfe\xff<1-byte char count><UTF-16LE text>`, alternating
  field-name/value pairs -- verified directly against real fixture bytes,
  not assumed from the investigation's prose summary.
- `Station.apd`/`Station.apx` (and similar proprietary binary shells, e.g.
  `.xma`) embed one or more **raw zlib streams with no gzip/zip wrapper**,
  found by scanning for zlib header bytes and validating with a bounded
  decompress -- not by relying on marker text or file names, since not
  every fixture's stream carries one.
- On the newest fixtures, a decompressed `STSource` stream is plain XML
  (`<STExchangeFile><STSource>...</STSource><D1 ...>...</D1></STExchangeFile>`)
  and is captured structurally. On the oldest fixtures, the same content is
  wrapped in a distinct, only partially-decoded .NET `BinaryWriter` string
  framing -- retained as raw bytes with an opportunistic content-label
  guess (a substring search for a known marker, never claimed as a real
  parse), diagnosed unsupported, not guessed at further.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
import zlib

_ZLIB_HEADER_SECOND_BYTES = (0x01, 0x5E, 0x9C, 0xDA)
# Opportunistic classification only for content this project cannot yet
# decode (the binary-framed shape) -- naming what was recognized, not
# claiming it was parsed. Order matters: checked as literal substrings.
_KNOWN_CONTENT_LABELS = ("STExchangeFile", "FBDExchangeFile", "TABExchangeFile")
_UNITY_SETTINGS_LABEL = re.compile(rb"unity\.[A-Za-z]+")


@dataclass(frozen=True)
class CaptureLimits:
    max_input_bytes: int = 64 * 1024 * 1024
    max_member_bytes: int = 32 * 1024 * 1024
    max_expanded_bytes: int = 16 * 1024 * 1024
    max_members: int = 2048
    max_archive_depth: int = 6
    max_zlib_streams_per_member: int = 64

    def __post_init__(self) -> None:
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Capture limits must be positive")


@dataclass(frozen=True)
class SourceLocation:
    input_sha256: str
    # Ordinal disambiguates duplicate member/stream names at every nesting level.
    members: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    source: SourceLocation


@dataclass
class CapturedSection:
    """A generic, fully-retained XML element tree -- no per-format spec
    matching at this granularity (Milestone 1 has exactly one known shape,
    `STExchangeFile`/`STSource`/`D1`); every element and attribute is kept
    regardless of whether the mapping layer interprets it.
    """

    tag: str
    raw_attributes: dict[str, str]
    text: str | None
    ordered_children: list["CapturedSection"] = field(default_factory=list)


@dataclass
class CapturedArtifact:
    name: str
    source: SourceLocation
    raw_bytes: bytes | None
    sha256: str | None
    kind: str = "opaque"
    directory: bool = False
    declared_size: int | None = None
    members: list["CapturedArtifact"] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    # kind == "xml" or "structured_text": the parsed element tree.
    section: CapturedSection | None = None
    # kind == "station_properties": STATION.CTX's decoded name/value pairs.
    station_properties: dict[str, str] | None = None
    # Set whenever a stream's own content type could be identified, whether
    # or not it could actually be parsed (e.g. "STExchangeFile" detected by
    # substring search inside an undecoded binary-framed stream). Never a
    # claim that the content was understood, only that it was recognized.
    content_label: str | None = None

    def report(self, code: str, message: str) -> None:
        self.diagnostics.append(Diagnostic(code, message, self.source))


@dataclass
class _Budget:
    expanded: int = 0
    members: int = 0


def _capture_xml(element: ET.Element) -> CapturedSection:
    return CapturedSection(
        tag=str(element.tag), raw_attributes=dict(element.attrib), text=element.text,
        ordered_children=[_capture_xml(child) for child in element],
    )


def _decode_station_ctx(data: bytes) -> tuple[dict[str, str], str | None]:
    """Decode STATION.CTX's `\\xff\\xfe\\xff<len><UTF-16LE text>` framing.

    Verified directly against real fixture bytes (not just the
    investigation doc's prose): the marker is followed by one length byte
    counting UTF-16 *characters*, then that many 2-byte code units, no
    terminator. Fields alternate name/value; an odd count or a frame that
    doesn't start with the marker is retained as raw evidence and
    diagnosed, not guessed at. Returns (properties, failure_message);
    failure_message is None on success.
    """
    fields: list[str] = []
    i = 0
    while i < len(data):
        if data[i:i + 3] != b"\xff\xfe\xff":
            return {}, f"STATION.CTX framing broke at byte offset {i}; content retained but not decoded"
        length = data[i + 3]
        i += 4
        chunk = data[i:i + length * 2]
        i += length * 2
        try:
            fields.append(chunk.decode("utf-16-le"))
        except UnicodeDecodeError:
            return {}, f"STATION.CTX field at byte offset {i} is not valid UTF-16; content retained but not decoded"
    if len(fields) % 2 != 0:
        return {}, f"STATION.CTX has {len(fields)} fields, an odd count; cannot pair name/value reliably"
    return dict(zip(fields[0::2], fields[1::2])), None


def _extract_zlib_streams(data: bytes, limits: CaptureLimits) -> list[tuple[int, bytes]]:
    """Scan for raw zlib streams (no gzip/zip wrapper) and validate each by

    decompressing it fully within a bounded output size. A candidate that
    doesn't reach its own stream end (`zlib` never reports `eof`) or would
    exceed the bound is rejected outright, not kept truncated -- a partial
    result here would misrepresent incomplete data as complete evidence.
    """
    streams: list[tuple[int, bytes]] = []
    seen_end: set[int] = set()
    for offset in range(len(data) - 1):
        if data[offset] != 0x78 or data[offset + 1] not in _ZLIB_HEADER_SECOND_BYTES:
            continue
        decompressor = zlib.decompressobj()
        try:
            out = decompressor.decompress(data[offset:], limits.max_expanded_bytes + 1)
        except zlib.error:
            continue
        if not decompressor.eof or len(out) > limits.max_expanded_bytes:
            continue
        end = len(data) - len(decompressor.unused_data)
        if end in seen_end:
            continue
        seen_end.add(end)
        streams.append((offset, out))
        if len(streams) >= limits.max_zlib_streams_per_member:
            break
    return streams


def _detect_content_label(data: bytes) -> str | None:
    for label in _KNOWN_CONTENT_LABELS:
        if label.encode("ascii") in data:
            return label
    match = _UNITY_SETTINGS_LABEL.search(data)
    if match:
        return "unity settings table"
    return None


def _looks_like_xml(data: bytes) -> bool:
    stripped = data.lstrip(b"\xef\xbb\xbf").lstrip()
    return stripped[:5] == b"<?xml"


def _inspect_xml(artifact: CapturedArtifact, data: bytes) -> None:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        artifact.kind = "opaque"
        artifact.report("xml_capture_error", str(error))
        return
    artifact.section = _capture_xml(root)
    if root.tag == "STExchangeFile":
        artifact.kind = "structured_text"
    else:
        artifact.kind = "xml"
        artifact.report("unclassified_scadapack_xml_root",
                         f"Root element {root.tag!r} is retained structurally but not yet mapped")
    artifact.content_label = root.tag


def _inspect_zlib_shell(artifact: CapturedArtifact, limits: CaptureLimits) -> None:
    data = artifact.raw_bytes
    assert data is not None
    streams = _extract_zlib_streams(data, limits)
    if not streams:
        artifact.kind = "opaque"
        return
    artifact.kind = "zlib_container"
    for index, (offset, decompressed) in enumerate(streams):
        member_name = f"stream[{index}]@0x{offset:x}"
        member = CapturedArtifact(
            member_name,
            SourceLocation(artifact.source.input_sha256, artifact.source.members + ((index, member_name),)),
            decompressed, sha256(decompressed).hexdigest(),
        )
        artifact.members.append(member)
        if _looks_like_xml(decompressed):
            _inspect_xml(member, decompressed)
        else:
            member.content_label = _detect_content_label(decompressed)
            if member.content_label is not None:
                member.kind = "binary_framed"
                member.report("unsupported_binary_framed_stream",
                               f"Recognized as {member.content_label!r} by a content marker, but this "
                               "stream's own .NET BinaryWriter string framing is not decoded yet "
                               "(see docs/architecture/scadapack-rcz-format.md); retained as evidence")
            else:
                member.kind = "opaque"


def _inspect(artifact: CapturedArtifact, limits: CaptureLimits, budget: _Budget, depth: int) -> None:
    data = artifact.raw_bytes
    if data is None or artifact.directory:
        return
    if data.startswith(b"PK\x03\x04"):
        artifact.kind = "archive"
        if depth >= limits.max_archive_depth:
            artifact.report("archive_depth_limit", "Archive retained without opening at depth limit")
            return
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                for index, info in enumerate(archive.infolist()):
                    if budget.members >= limits.max_members:
                        artifact.report("member_count_limit", "Remaining members retained in original archive only")
                        break
                    budget.members += 1
                    source = SourceLocation(artifact.source.input_sha256,
                                            artifact.source.members + ((index, info.filename),))
                    member = CapturedArtifact(info.filename, source, None, None,
                                              directory=info.is_dir(), declared_size=info.file_size)
                    artifact.members.append(member)
                    if info.flag_bits & 1:
                        member.report("encrypted_member", "Encrypted member retained in parent archive")
                        continue
                    available = min(limits.max_member_bytes, limits.max_expanded_bytes - budget.expanded)
                    if info.file_size > available:
                        member.report("expanded_size_limit", "Member exceeds capture budget; retained in parent archive")
                        continue
                    try:
                        with archive.open(info) as stream:
                            payload = stream.read(available + 1)
                        budget.expanded += len(payload)
                        if len(payload) > available:
                            member.report("expanded_size_limit", "Expanded member exceeds capture budget")
                            continue
                        member.raw_bytes = payload
                        member.sha256 = sha256(payload).hexdigest()
                        if member.name.upper().endswith("STATION.CTX"):
                            properties, failure = _decode_station_ctx(payload)
                            if failure is not None:
                                member.kind = "opaque"
                                member.report("unresolved_station_ctx_framing", failure)
                            else:
                                member.kind = "station_properties"
                                member.station_properties = properties
                        else:
                            _inspect(member, limits, budget, depth + 1)
                    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError, EOFError, zlib.error) as error:
                        member.report("member_read_error", str(error))
        except (zipfile.BadZipFile, OSError, EOFError) as error:
            artifact.report("archive_read_error", str(error))
    elif _looks_like_xml(data):
        _inspect_xml(artifact, data)
    else:
        _inspect_zlib_shell(artifact, limits)


def capture_bytes(data: bytes, *, name: str = "station.rcz", limits: CaptureLimits | None = None) -> CapturedArtifact:
    """Capture one input, retaining bytes even when inspection is unsupported."""
    limits = limits or CaptureLimits()
    digest = sha256(data).hexdigest()
    artifact = CapturedArtifact(name, SourceLocation(digest), data, digest)
    if len(data) > limits.max_input_bytes:
        artifact.report("input_size_limit", "Input retained without inspection because it exceeds the limit")
    else:
        _inspect(artifact, limits, _Budget(), 0)
    return artifact


def capture_file(path: str | Path, *, limits: CaptureLimits | None = None) -> CapturedArtifact:
    """Read a bounded file. Oversized files raise before loading; source is untouched."""
    limits = limits or CaptureLimits()
    path = Path(path)
    with path.open("rb") as stream:
        data = stream.read(limits.max_input_bytes + 1)
    return capture_bytes(data, name=path.name, limits=limits)
