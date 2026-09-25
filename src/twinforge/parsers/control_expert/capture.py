"""Bounded archive/XML inspection with original-byte preservation.

No filesystem extraction, external XML resolution, or neutral-model conversion.
Unreadable members retain their identity and an explicit diagnostic; their stored
representation remains in the original parent archive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import zlib

from twinforge.schema.control_expert import EXCHANGE_SPEC, FB_EXCHANGE_SPEC, ElementSpec

# Every recognized root shape tried in order, e.g. a project (FEFExchangeFile/
# ZEFExchangeFile) or a standalone Derived Function Block export
# (FBExchangeFile) -- callers that pass their own single ElementSpec still
# work unchanged (_inspect normalizes to a tuple either way).
CONTROL_EXPERT_SPECS: tuple[ElementSpec, ...] = (EXCHANGE_SPEC, FB_EXCHANGE_SPEC)


@dataclass(frozen=True)
class CaptureLimits:
    max_input_bytes: int = 64 * 1024 * 1024
    max_member_bytes: int = 32 * 1024 * 1024
    max_expanded_bytes: int = 128 * 1024 * 1024
    max_members: int = 2048
    max_archive_depth: int = 2
    max_xml_depth: int = 128
    max_xml_nodes: int = 250_000

    def __post_init__(self) -> None:
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Capture limits must be positive")


@dataclass(frozen=True)
class SourceLocation:
    input_sha256: str
    # Ordinal disambiguates duplicate member names at every nesting level.
    members: tuple[tuple[int, str], ...] = ()
    xml_path: str = ""


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    source: SourceLocation


@dataclass
class CapturedSection:
    tag: str
    source: SourceLocation
    spec: ElementSpec | None
    raw_attributes: dict[str, str]
    text: str | None
    tail: str | None
    ordered_children: list[CapturedSection] = field(default_factory=list)

    @property
    def extra_attributes(self) -> dict[str, str]:
        known = self.spec.attributes if self.spec else frozenset()
        return {key: value for key, value in self.raw_attributes.items() if key not in known}


@dataclass
class CapturedArtifact:
    name: str
    source: SourceLocation
    raw_bytes: bytes | None
    sha256: str | None
    kind: str = "opaque"
    directory: bool = False
    declared_size: int | None = None
    crc32: int | None = None
    members: list[CapturedArtifact] = field(default_factory=list)
    section: CapturedSection | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def report(self, code: str, message: str) -> None:
        self.diagnostics.append(Diagnostic(code, message, self.source))


@dataclass
class _Budget:
    expanded: int = 0
    members: int = 0


class _BoundedTreeBuilder(ET.TreeBuilder):
    def __init__(self, limits: CaptureLimits):
        super().__init__(insert_comments=True, insert_pis=True)
        self.limits = limits
        self.depth = 0
        self.nodes = 0

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("DTD declarations are not supported; original XML retained")

    def start(self, tag: str, attrs: dict[str, str]) -> ET.Element:
        self.depth += 1
        self.nodes += 1
        if self.depth > self.limits.max_xml_depth or self.nodes > self.limits.max_xml_nodes:
            raise ValueError("XML depth or node limit exceeded")
        return super().start(tag, attrs)

    def end(self, tag: str) -> ET.Element:
        self.depth -= 1
        return super().end(tag)


def _capture_section(
    node: ET.Element, spec: ElementSpec | None, source: SourceLocation,
) -> CapturedSection:
    tag = ("#comment" if node.tag is ET.Comment else
           "#processing-instruction" if node.tag is ET.ProcessingInstruction else str(node.tag))
    section = CapturedSection(tag, source, spec, dict(node.attrib), node.text, node.tail)
    children = {child.name: child for child in spec.children} if spec else {}
    for index, child in enumerate(node):
        child_source = SourceLocation(source.input_sha256, source.members,
                                      f"{source.xml_path}/child[{index}]")
        section.ordered_children.append(_capture_section(child, children.get(child.tag), child_source))
    return section


def _inspect(
    artifact: CapturedArtifact, limits: CaptureLimits, budget: _Budget,
    depth: int, spec: ElementSpec | tuple[ElementSpec, ...],
) -> None:
    data = artifact.raw_bytes
    if data is None or artifact.directory:
        return
    suffix = Path(artifact.name).suffix.lower()
    if suffix in {".zip", ".zef"} or data.startswith(b"PK\x03\x04"):
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
                                              directory=info.is_dir(), declared_size=info.file_size,
                                              crc32=info.CRC)
                    artifact.members.append(member)
                    if info.flag_bits & 1:
                        member.report("encrypted_member", "Encrypted member retained in parent archive")
                        continue
                    available = min(limits.max_member_bytes,
                                    limits.max_expanded_bytes - budget.expanded)
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
                        _inspect(member, limits, budget, depth + 1, spec)
                    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError, EOFError, zlib.error) as error:
                        member.report("member_read_error", str(error))
        except (zipfile.BadZipFile, OSError, EOFError) as error:
            artifact.report("archive_read_error", str(error))
    elif suffix in {".xef", ".xml", ".xpdf", ".xdb"}:
        artifact.kind = "xml"
        try:
            root = ET.fromstring(data, parser=ET.XMLParser(target=_BoundedTreeBuilder(limits)))
            specs = spec if isinstance(spec, tuple) else (spec,)
            matching = next((s for s in specs if root.tag in (s.name, *s.root_aliases)), None)
            source = SourceLocation(artifact.source.input_sha256, artifact.source.members, f"/{root.tag}")
            artifact.section = _capture_section(root, matching, source)
            if matching is None:
                artifact.report("unclassified_xml", "No matching root specification; entire tree retained")
            else:
                pending = [artifact.section]
                unknown_elements = unknown_attributes = 0
                while pending:
                    section = pending.pop()
                    if not section.tag.startswith("#"):
                        unknown_elements += int(section.spec is None)
                        unknown_attributes += len(section.extra_attributes)
                    pending.extend(section.ordered_children)
                if unknown_elements or unknown_attributes:
                    artifact.diagnostics.append(Diagnostic(
                        "unclassified_content",
                        f"Retained {unknown_elements} unclassified elements and "
                        f"{unknown_attributes} unclassified attributes; mapping is incomplete",
                        source,
                    ))
        except (ET.ParseError, ValueError) as error:
            artifact.report("xml_capture_error", str(error))


def capture_bytes(
    data: bytes, *, name: str = "project.zef", limits: CaptureLimits | None = None,
    spec: ElementSpec | tuple[ElementSpec, ...] = CONTROL_EXPERT_SPECS,
) -> CapturedArtifact:
    """Capture one input, retaining bytes even when inspection is unsupported."""
    limits = limits or CaptureLimits()
    digest = sha256(data).hexdigest()
    artifact = CapturedArtifact(name, SourceLocation(digest), data, digest)
    if len(data) > limits.max_input_bytes:
        artifact.report("input_size_limit", "Input retained without inspection because it exceeds the limit")
    else:
        _inspect(artifact, limits, _Budget(), 0, spec)
    return artifact


def capture_file(
    path: str | Path, *, limits: CaptureLimits | None = None,
    spec: ElementSpec | tuple[ElementSpec, ...] = CONTROL_EXPERT_SPECS,
) -> CapturedArtifact:
    """Read a bounded file. Oversized files raise before loading; source is untouched."""
    limits = limits or CaptureLimits()
    path = Path(path)
    with path.open("rb") as stream:
        data = stream.read(limits.max_input_bytes + 1)
    if len(data) > limits.max_input_bytes:
        raise ValueError(f"Input exceeds max_input_bytes; original file remains at {path}")
    return capture_bytes(data, name=path.name, limits=limits, spec=spec)
