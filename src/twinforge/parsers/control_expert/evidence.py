"""Neutral source snapshots shared by Control Expert mapping stages."""
from twinforge.model import SourceExtension, SourceNode

from .capture import CapturedSection


def snapshot(node: CapturedSection) -> SourceNode:
    return SourceNode(node.tag, dict(node.raw_attributes), node.text, node.tail,
                      [snapshot(child) for child in node.ordered_children])


def source_extension(node: CapturedSection) -> SourceExtension:
    return SourceExtension("control-expert", snapshot(node), {
        "input_sha256": node.source.input_sha256,
        "members": node.source.members,
        "xml_path": node.source.xml_path,
    })
