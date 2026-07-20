# src/twinforge/model/tag.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension
from .datatype import Datatype


@dataclass
class Tag:
    name: str = ""
    tag_type: str | None = None
    data_type: str | None = None
    data_type_definition: Datatype | None = None
    dimensions: str | None = None
    radix: str | None = None
    constant: bool | None = None
    alias_for: str | None = None
    external_access: str | None = None
    permission_set: str | None = None
    description: str | None = None
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    metadata: dict = field(default_factory=dict)
    parent: Any | None = field(default=None, repr=False)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
