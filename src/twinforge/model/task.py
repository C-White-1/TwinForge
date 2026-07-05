# src/twinforge/model/task.py

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    parent: object | None = None
    metadata: dict = field(default_factory=dict)
