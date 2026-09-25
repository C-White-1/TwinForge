"""Neutral source snapshots for SCADAPack mapping."""
from twinforge.model import SourceExtension, SourceNode

from .capture import CapturedSection, SourceLocation


def snapshot(node: CapturedSection) -> SourceNode:
    return SourceNode(node.tag, dict(node.raw_attributes), node.text, None,
                      [snapshot(child) for child in node.ordered_children])


def source_extension(section: CapturedSection, source: SourceLocation) -> SourceExtension:
    return SourceExtension("scadapack", snapshot(section), {
        "input_sha256": source.input_sha256,
        "members": source.members,
    })
