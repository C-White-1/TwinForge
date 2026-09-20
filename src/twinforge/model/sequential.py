"""Neutral sequential-chart structure. Connectivity edges are populated only by
a separate resolver from evidenced grid adjacency and explicit links; nothing
here infers them from parsing alone, and execution semantics remain unresolved.
"""
from dataclasses import dataclass, field

from .source_extension import SourceExtension


@dataclass
class SequentialElement:
    kind: str
    properties: dict[str, str] = field(default_factory=dict)
    text: str | None = None
    children: list["SequentialElement"] = field(default_factory=list)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
    reference_status: str | None = None
    target_definition_index: int | None = None
    target_element_path: list[int] | None = None
    binding_kind: str | None = None
    target_symbol_name: str | None = None
    target_member_name: str | None = None
    member_data_type: str | None = None


@dataclass
class SequentialEdge:
    """One resolved step<->transition edge; not a memory, timing or truth claim."""
    source_path: list[int]
    destination_path: list[int]
    basis: str


@dataclass
class SequentialChart:
    name: str | None = None
    elements: list[SequentialElement] = field(default_factory=list)
    transition_definitions: list[SequentialElement] = field(default_factory=list)
    connectivity_resolved: bool = False
    connectivity_edges: list[SequentialEdge] = field(default_factory=list)
    execution_resolved: bool = False
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
