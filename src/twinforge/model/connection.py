# src/twinforge/model/connection.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Connection:
    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    parent: Any | None = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)
