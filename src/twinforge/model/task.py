# src/twinforge/model/task.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .source_extension import SourceExtension

if TYPE_CHECKING:
    from .program import Program


@dataclass
class Task:
    name: str = ""
    task_type: str | None = None
    rate: int | None = None
    priority: int | None = None
    watchdog: int | None = None
    disable_update_outputs: bool | None = None
    inhibited: bool | None = None
    event_trigger: str | None = None
    description: str | None = None
    scheduled_program_names: list[str] = field(default_factory=list)
    scheduled_programs: list[Program] = field(default_factory=list)
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    parent: object | None = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
