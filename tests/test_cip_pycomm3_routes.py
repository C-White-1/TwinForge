import json

import pytest

from twinforge.discovery.cip_pycomm3_routes import (
    Pycomm3RouteEncodingError,
    encode_pycomm3_route,
    pycomm3_route_encoding_json,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget


def _route(*segments: CipRouteSegment) -> CipRouteDeclaration:
    return CipRouteDeclaration(
        gateway=DiscoveryTarget(address="192.168.1.10"),
        segments=segments,
        maximum_depth=len(segments),
    )


def test_encoder_matches_pycomm3_padded_epath_bytes() -> None:
    route = _route(
        CipRouteSegment(port=1, link=0),
        CipRouteSegment(port=2, link="192.168.2.20"),
        CipRouteSegment(port=3, link=b"\x01\x02"),
    )

    encoding = encode_pycomm3_route(route)
    document = json.loads(pycomm3_route_encoding_json(encoding))

    expected = "0100120c3139322e3136382e322e323013020102"
    assert encoding.encoded_path.hex() == expected
    assert encoding.encoded_path_with_word_count.hex() == f"0a{expected}"
    assert document["encoding"] == "padded_epath"
    assert document["path_word_count"] == 10
    assert document["adapter"] == "pycomm3"
    assert document["route"]["segments"][2] == {
        "port": 3,
        "link_type": "bytes",
        "link": "0102",
    }


def test_encoder_preserves_padding_for_single_byte_link() -> None:
    encoding = encode_pycomm3_route(
        _route(CipRouteSegment(port=1, link=7))
    )

    assert encoding.encoded_path == b"\x01\x07"
    assert encoding.encoded_path_with_word_count == b"\x01\x01\x07"


@pytest.mark.parametrize(
    "segment",
    [
        CipRouteSegment(port=256, link=0),
        CipRouteSegment(port=1, link=256),
        CipRouteSegment(port=1, link="256"),
        CipRouteSegment(port=1, link=b"x" * 256),
    ],
)
def test_encoder_reports_pycomm3_representation_limits(
    segment: CipRouteSegment,
) -> None:
    with pytest.raises(Pycomm3RouteEncodingError, match="pycomm3"):
        encode_pycomm3_route(_route(segment))


def test_encoder_rejects_invalid_text_link_without_network_access() -> None:
    route = _route(CipRouteSegment(port=2, link="not-an-ip-address"))

    with pytest.raises(Pycomm3RouteEncodingError, match="could not encode"):
        encode_pycomm3_route(route)
