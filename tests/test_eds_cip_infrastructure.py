from __future__ import annotations

from pathlib import Path

from twinforge.assembly.eds_cip_infrastructure import (
    EdsLogicalSegmentType,
    assess_eds_cip_infrastructure,
    decode_eds_logical_path,
)
from twinforge.parsers.eds import EDSParser


def test_decodes_eds_connection_path_and_builds_exact_candidates() -> None:
    source = Path(__file__).parent / "data" / "eds" / "cip-infrastructure.eds"

    assessment = assess_eds_cip_infrastructure(EDSParser().parse(source))

    first_segments = assessment.segments[0][1]
    assert [(item.segment_type, item.value) for item in first_segments] == [
        (EdsLogicalSegmentType.CLASS, 4),
        (EdsLogicalSegmentType.INSTANCE, 102),
        (EdsLogicalSegmentType.CONNECTION_POINT, 133),
        (EdsLogicalSegmentType.CONNECTION_POINT, 132),
    ]
    first = assessment.candidates[:3]
    assert [item.request.instance for item in first] == [102, 133, 132]
    assert [item.endpoint_reference for item in first] == [None, "Assem2", "Assem1"]
    assert [item.declared_size for item in first] == [0, 496, 500]
    assert all(item.request.attribute == 3 for item in first)
    assert all(item.request.object_type.class_code == 4 for item in first)
    assert assessment.diagnostics == ()


def test_decodes_sixteen_bit_logical_segments_with_padding() -> None:
    segments = decode_eds_logical_path(
        bytes.fromhex("21 00 04 00 25 00 02 01 2D 00 34 12")
    )

    assert [(item.segment_type, item.value) for item in segments] == [
        (EdsLogicalSegmentType.CLASS, 4),
        (EdsLogicalSegmentType.INSTANCE, 258),
        (EdsLogicalSegmentType.CONNECTION_POINT, 0x1234),
    ]
    assert segments[1].encoded_hex == "25000201"


def test_retains_unsupported_path_as_diagnostic(tmp_path: Path) -> None:
    source = tmp_path / "unsupported.eds"
    source.write_text(
        """
[Device]
VendCode = 1;
ProdType = 12;
ProdCode = 7;
MajRev = 1;
MinRev = 0;
ProdName = "Fixture";
[Connection Manager]
Connection1 = 2,4,Param1,4,Assem2,Param1,8,Assem1,,,0,,"Test","","91 01";
""",
        encoding="utf-8",
    )

    assessment = assess_eds_cip_infrastructure(EDSParser().parse(source))

    assert assessment.candidates == ()
    assert assessment.segments == ()
    assert assessment.diagnostics[0].code == "eds_connection_path_unsupported"
    assert "0x91" in assessment.diagnostics[0].message
    assert assessment.diagnostics[0].path_hex == "9101"
