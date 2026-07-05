# src/twinforge/model/device.py

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Device:
    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    metadata: dict = field(default_factory=dict)
