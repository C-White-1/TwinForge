# src/twinforge/model/tag.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tag:
    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    metadata: dict = field(default_factory=dict)
    parent: Any | None = field(default=None, repr=False)
