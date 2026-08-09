"""Pure translation from TwinForge route declarations to pycomm3 EPATHs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

from pycomm3 import PADDED_EPATH, PortSegment

from .cip_routes import CipRouteDeclaration, CipRouteSegment, cip_route_data


class Pycomm3RouteEncodingError(ValueError):
    """A declared route cannot be represented by the installed pycomm3 API."""


@dataclass(frozen=True)
class Pycomm3RouteEncoding:
    """Encoded path evidence without a driver or network connection."""

    route: CipRouteDeclaration
    encoded_path: bytes
    encoded_path_with_word_count: bytes
    adapter: str
    adapter_version: str


def encode_pycomm3_route(
    route: CipRouteDeclaration,
) -> Pycomm3RouteEncoding:
    """Encode an exact route using pycomm3's padded EPATH implementation."""
    segments = tuple(_pycomm3_segment(item) for item in route.segments)
    try:
        encoded = PADDED_EPATH.encode(segments)
        encoded_with_count = PADDED_EPATH.encode(segments, length=True)
    except Exception as error:
        raise Pycomm3RouteEncodingError(
            f"pycomm3 could not encode CIP route {route.key}: {error}"
        ) from error
    return Pycomm3RouteEncoding(
        route=route,
        encoded_path=encoded,
        encoded_path_with_word_count=encoded_with_count,
        adapter="pycomm3",
        adapter_version=version("pycomm3"),
    )


def pycomm3_route_encoding_data(
    encoding: Pycomm3RouteEncoding,
) -> dict[str, Any]:
    """Return deterministic route declaration and encoded-byte evidence."""
    return {
        "route": cip_route_data(encoding.route),
        "adapter": encoding.adapter,
        "adapter_version": encoding.adapter_version,
        "encoding": "padded_epath",
        "encoded_path_hex": encoding.encoded_path.hex(),
        "encoded_path_with_word_count_hex": (
            encoding.encoded_path_with_word_count.hex()
        ),
        "path_word_count": len(encoding.encoded_path) // 2,
    }


def pycomm3_route_encoding_json(encoding: Pycomm3RouteEncoding) -> str:
    """Serialize declaration and encoded evidence with a final newline."""
    return json.dumps(
        pycomm3_route_encoding_data(encoding),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _pycomm3_segment(segment: CipRouteSegment) -> PortSegment:
    if segment.port > 0xFF:
        raise Pycomm3RouteEncodingError(
            "installed pycomm3 PortSegment supports port values up to 255"
        )
    if isinstance(segment.link, int) and segment.link > 0xFF:
        raise Pycomm3RouteEncodingError(
            "installed pycomm3 PortSegment supports integer links up to 255"
        )
    if isinstance(segment.link, bytes) and len(segment.link) > 0xFF:
        raise Pycomm3RouteEncodingError(
            "installed pycomm3 PortSegment supports links up to 255 bytes"
        )
    if isinstance(segment.link, str) and segment.link.isnumeric():
        if int(segment.link) > 0xFF:
            raise Pycomm3RouteEncodingError(
                "installed pycomm3 PortSegment supports numeric links up to 255"
            )
    try:
        return PortSegment(segment.port, segment.link)
    except Exception as error:
        raise Pycomm3RouteEncodingError(
            f"pycomm3 rejected route segment {segment.key}: {error}"
        ) from error
