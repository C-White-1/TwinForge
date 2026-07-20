from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceNode:
    """Format-neutral snapshot of one source document node."""

    name: str
    attributes: dict[str, str] = field(default_factory=dict)
    text: str | None = None
    tail: str | None = None
    children: list["SourceNode"] = field(default_factory=list)


@dataclass
class SourceExtension:
    """Source-format data retained alongside a vendor-neutral model object."""

    format: str
    root: SourceNode
    metadata: dict[str, Any] = field(default_factory=dict)
