# src/twinforge/model/connection.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension


@dataclass
class Connection:
    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    connection_type: str | None = None
    parent: Any | None = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
