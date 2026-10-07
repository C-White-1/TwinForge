"""Neutral source snapshots for Machine Expert – Basic mapping."""
from twinforge.model import SourceExtension, SourceNode

from .capture import CapturedSection


def snapshot(node: CapturedSection) -> SourceNode:
    return SourceNode(node.tag, dict(node.raw_attributes), node.text, node.tail,
                      [snapshot(child) for child in node.ordered_children])


def source_extension(node: CapturedSection) -> SourceExtension:
    return SourceExtension("machine-expert-basic", snapshot(node), {
        "input_sha256": node.source.input_sha256,
        "xml_path": node.source.xml_path,
    })
