# src/twinforge/model/datatype.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension


@dataclass
class DatatypeMember:
    name: str = ""
    data_type_name: str | None = None
    data_type: "Datatype | None" = None
    dimension: str | None = None
    radix: str | None = None
    hidden: bool | None = None
    external_access: str | None = None
    description: str | None = None
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)


@dataclass
class Datatype:
    name: str = ""
    family: str | None = None
    classification: str | None = None
    description: str | None = None
    members: list[DatatypeMember] = field(default_factory=list)
    parent: Any | None = field(default=None, repr=False)
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    metadata: dict = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
