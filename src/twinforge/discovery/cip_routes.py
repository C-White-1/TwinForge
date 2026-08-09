"""Explicit, bounded CIP route declarations for future routed discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .contracts import DiscoveryTarget


@dataclass(frozen=True)
class CipRouteSegment:
    """One CIP port segment with its exact link address preserved."""

    port: int
    link: int | str | bytes

    def __post_init__(self) -> None:
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("CIP route port must be an integer")
        if self.port <= 0 or self.port > 0xFFFF:
            raise ValueError("CIP route port must be between 1 and 65535")
        if isinstance(self.link, bool):
            raise TypeError("CIP route link must not be a boolean")
        if isinstance(self.link, int) and self.link < 0:
            raise ValueError("integer CIP route links must not be negative")
        if isinstance(self.link, str) and not self.link:
            raise ValueError("text CIP route links must not be empty")
        if isinstance(self.link, bytes) and not self.link:
            raise ValueError("binary CIP route links must not be empty")
        if not isinstance(self.link, (int, str, bytes)):
            raise TypeError("CIP route link must be an integer, text, or bytes")

    @property
    def key(self) -> str:
        """Return a type-qualified representation suitable for stable keys."""
        if isinstance(self.link, int):
            link = f"integer:{self.link}"
        elif isinstance(self.link, bytes):
            link = f"bytes:{self.link.hex()}"
        else:
            link = f"text:{self.link}"
        return f"port:{self.port}|link:{link}"


@dataclass(frozen=True)
class CipRouteDeclaration:
    """One authorized route through an exact gateway with a depth limit."""

    gateway: DiscoveryTarget
    segments: tuple[CipRouteSegment, ...]
    maximum_depth: int
    label: str | None = None

    def __post_init__(self) -> None:
        if self.gateway.route:
            raise ValueError(
                "gateway must not use the legacy DiscoveryTarget route tuple"
            )
        if not self.segments:
            raise ValueError("CIP route must contain at least one segment")
        if isinstance(self.maximum_depth, bool) or self.maximum_depth <= 0:
            raise ValueError("maximum_depth must be a positive integer")
        if len(self.segments) > self.maximum_depth:
            raise ValueError("CIP route exceeds its declared maximum depth")
        if self.label is not None and self.label != self.label.strip():
            raise ValueError("route label must not contain surrounding whitespace")

    @property
    def key(self) -> str:
        """Return a deterministic gateway-and-path identity."""
        path = "/".join(segment.key for segment in self.segments)
        return f"{self.gateway.key}|{path}"


def cip_route_data(route: CipRouteDeclaration) -> dict[str, Any]:
    """Return a lossless, JSON-compatible route declaration."""
    return {
        "gateway": {
            "address": route.gateway.address,
            "label": route.gateway.label,
        },
        "segments": [_segment_data(segment) for segment in route.segments],
        "maximum_depth": route.maximum_depth,
        "label": route.label,
        "key": route.key,
    }


def cip_route_json(route: CipRouteDeclaration) -> str:
    """Serialize a route declaration deterministically with a final newline."""
    return json.dumps(cip_route_data(route), indent=2, ensure_ascii=False) + "\n"


def _segment_data(segment: CipRouteSegment) -> dict[str, Any]:
    if isinstance(segment.link, int):
        link_type = "integer"
        link_value: int | str = segment.link
    elif isinstance(segment.link, bytes):
        link_type = "bytes"
        link_value = segment.link.hex()
    else:
        link_type = "text"
        link_value = segment.link
    return {
        "port": segment.port,
        "link_type": link_type,
        "link": link_value,
    }
