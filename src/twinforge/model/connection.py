# src/twinforge/model/connection.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension


@dataclass
class Connection:
    """A logical or cyclic connection between communication endpoints."""

    name: str = ""
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    connection_type: str | None = None
    requested_packet_interval_microseconds: int | None = None
    input_connection_point: int | None = None
    output_connection_point: int | None = None
    input_size_bytes: int | None = None
    output_size_bytes: int | None = None
    unicast: bool | None = None
    parent: Any | None = field(default=None, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(
        default_factory=list,
        repr=False,
    )
