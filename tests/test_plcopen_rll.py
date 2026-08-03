from twinforge.exporters.plcopen_rll import (
    SUPPORTED_RLL_INSTRUCTIONS,
    parse_supported_rung,
)


def test_parses_tof_for_an_evidenced_target_without_claiming_generic_support():
    parsed = parse_supported_rung("XIC(Enable)TOF(DelayTimer,?,?);")

    assert parsed is not None
    assert parsed.tail_conditions == (("XIC", "Enable"),)
    assert parsed.outputs == (("TOF", "DelayTimer,?,?"),)
    assert "TOF" not in SUPPORTED_RLL_INSTRUCTIONS


def test_rejects_tof_with_wrong_argument_count():
    assert parse_supported_rung("XIC(Enable)TOF(DelayTimer,?);") is None


def test_parses_rto_without_claiming_generic_support():
    parsed = parse_supported_rung("XIC(Enable)RTO(DelayTimer,?,?);")

    assert parsed is not None
    assert parsed.outputs == (("RTO", "DelayTimer,?,?"),)
    assert "RTO" not in SUPPORTED_RLL_INSTRUCTIONS
