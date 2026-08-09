import json

import pytest

from twinforge.discovery import (
    CipRouteDeclaration,
    CipRouteSegment,
    DiscoveryTarget,
    cip_route_json,
)


def test_route_preserves_typed_segments_and_serializes_deterministically() -> None:
    route = CipRouteDeclaration(
        gateway=DiscoveryTarget(
            address="192.168.1.10",
            label="lab gateway",
        ),
        segments=(
            CipRouteSegment(port=1, link=0),
            CipRouteSegment(port=2, link="192.168.2.20"),
            CipRouteSegment(port=3, link=b"\x01\x02"),
        ),
        maximum_depth=3,
        label="authorized test path",
    )

    document = json.loads(cip_route_json(route))

    assert document["gateway"] == {
        "address": "192.168.1.10",
        "label": "lab gateway",
    }
    assert document["segments"] == [
        {"port": 1, "link_type": "integer", "link": 0},
        {"port": 2, "link_type": "text", "link": "192.168.2.20"},
        {"port": 3, "link_type": "bytes", "link": "0102"},
    ]
    assert document["maximum_depth"] == 3
    assert "integer:0" in document["key"]
    assert "text:192.168.2.20" in document["key"]
    assert "bytes:0102" in document["key"]


def test_route_rejects_path_beyond_explicit_depth_limit() -> None:
    with pytest.raises(ValueError, match="maximum depth"):
        CipRouteDeclaration(
            gateway=DiscoveryTarget(address="192.168.1.10"),
            segments=(
                CipRouteSegment(port=1, link=0),
                CipRouteSegment(port=1, link=3),
            ),
            maximum_depth=1,
        )


def test_route_rejects_ambiguous_legacy_gateway_route() -> None:
    with pytest.raises(ValueError, match="legacy"):
        CipRouteDeclaration(
            gateway=DiscoveryTarget(address="192.168.1.10", route=(1, 0)),
            segments=(CipRouteSegment(port=1, link=0),),
            maximum_depth=1,
        )


@pytest.mark.parametrize(
    ("port", "link"),
    [(0, 0), (65536, 0), (1, -1), (1, ""), (1, b"")],
)
def test_route_rejects_invalid_segment(port: int, link: int | str | bytes) -> None:
    with pytest.raises((TypeError, ValueError)):
        CipRouteSegment(port=port, link=link)
