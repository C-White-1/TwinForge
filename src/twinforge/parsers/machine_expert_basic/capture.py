"""Bounded `.smbp` XML capture with original-byte preservation.

An `.smbp` is one UTF-8 (BOM-prefixed) XML document, not an archive; see
docs/architecture/machine-expert-basic-smbp-format.md. Implemented
independently per this project's per-format capture convention
(`parsers/control_expert/capture.py`, `parsers/scadapack/capture.py`).

No external XML resolution and no model conversion. Every element is
retained, whether or not the observed grammar in
`schema/machine_expert_basic` classifies it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.schema.machine_expert_basic import (
    ENCRYPTED_PROJECT_SPEC, PROJECT_SPEC, SPECS, ElementSpec,
)

_KINDS = {PROJECT_SPEC.name: "project", ENCRYPTED_PROJECT_SPEC.name: "encrypted_project"}


@dataclass(frozen=True)
class CaptureLimits:
    max_input_bytes: int = 64 * 1024 * 1024
    max_xml_depth: int = 128
    max_xml_nodes: int = 2_000_000

    def __post_init__(self) -> None:
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Capture limits must be positive")


@dataclass(frozen=True)
class SourceLocation:
    input_sha256: str
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
    raw_bytes: bytes
    sha256: str
    # "project", "encrypted_project", "xml" (unrecognized root) or "opaque".
    kind: str = "opaque"
    section: CapturedSection | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def report(self, code: str, message: str) -> None:
        self.diagnostics.append(Diagnostic(code, message, self.source))


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


def _capture_section(node: ET.Element, spec: ElementSpec | None, source: SourceLocation) -> CapturedSection:
    tag = ("#comment" if node.tag is ET.Comment else
           "#processing-instruction" if node.tag is ET.ProcessingInstruction else str(node.tag))
    section = CapturedSection(tag, source, spec, dict(node.attrib), node.text, node.tail)
    children = {child.name: child for child in spec.children} if spec else {}
    for index, child in enumerate(node):
        child_source = SourceLocation(source.input_sha256, f"{source.xml_path}/child[{index}]")
        section.ordered_children.append(_capture_section(child, children.get(child.tag), child_source))
    return section


def _unclassified(section: CapturedSection) -> tuple[int, int]:
    elements = attributes = 0
    pending = [section]
    while pending:
        node = pending.pop()
        if not node.tag.startswith("#"):
            elements += int(node.spec is None)
            attributes += len(node.extra_attributes)
        pending.extend(node.ordered_children)
    return elements, attributes


def capture_bytes(data: bytes, *, name: str = "project.smbp", limits: CaptureLimits | None = None) -> CapturedArtifact:
    """Capture one input, retaining its bytes even when inspection fails."""
    limits = limits or CaptureLimits()
    digest = sha256(data).hexdigest()
    artifact = CapturedArtifact(name, SourceLocation(digest), data, digest)
    if len(data) > limits.max_input_bytes:
        artifact.report("input_size_limit", "Input retained without inspection because it exceeds the limit")
        return artifact
    try:
        root = ET.fromstring(data, parser=ET.XMLParser(target=_BoundedTreeBuilder(limits)))
    except (ET.ParseError, ValueError) as error:
        artifact.report("xml_capture_error", str(error))
        return artifact
    spec = next((candidate for candidate in SPECS if candidate.name == root.tag), None)
    artifact.section = _capture_section(root, spec, SourceLocation(digest, f"/{root.tag}"))
    if spec is None:
        artifact.kind = "xml"
        artifact.report("unclassified_xml", f"Root element {root.tag!r} is not a recognized .smbp root; "
                                            "entire tree retained")
        return artifact
    artifact.kind = _KINDS[spec.name]
    elements, attributes = _unclassified(artifact.section)
    if elements or attributes:
        artifact.report("unclassified_content",
                        f"Retained {elements} unclassified elements and {attributes} unclassified "
                        "attributes; mapping is incomplete")
    return artifact


def capture_file(path: str | Path, *, limits: CaptureLimits | None = None) -> CapturedArtifact:
    """Read a bounded file. Oversized files raise before loading; source is untouched."""
    limits = limits or CaptureLimits()
    path = Path(path)
    with path.open("rb") as stream:
        data = stream.read(limits.max_input_bytes + 1)
    if len(data) > limits.max_input_bytes:
        raise ValueError(f"Input exceeds max_input_bytes; original file remains at {path}")
    return capture_bytes(data, name=path.name, limits=limits)
