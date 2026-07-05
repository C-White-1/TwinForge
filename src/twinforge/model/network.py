# src/twinforge/model/network.py

from __future__ import annotations

from dataclasses import dataclass, field

from .asset import Asset


@dataclass
class Network(Asset):
    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    metadata: dict = field(default_factory=dict)

    parent: object | None = None
