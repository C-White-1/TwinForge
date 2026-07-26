from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.exporters import (
    IECRequirement,
    emit_iec_st_unit,
)
from twinforge.ir import (
    IRDirection,
    IRNormalizationPolicy,
    IRUnitKind,
    lower_add_on_instruction,
    normalize_reusable_unit,
)
from twinforge.parsers import L5XParser


DATA = Path(__file__).parent / "data/aoi"


def _str_capacity():
    controller = next(
        L5XParser()
        .parse(DATA / "Str_Capacity_AOI.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["Str_Capacity"]
    report = analyze_structured_text_semantics(controller)
    return lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:Str_Capacity"
        },
    )


def test_preserve_policy_returns_original_unit_without_changes():
    source = _str_capacity()

    result = normalize_reusable_unit(source)

    assert result.unit is source
    assert result.changes == ()


def test_str_capacity_written_input_is_explicitly_promoted():
    source = _str_capacity()

    result = normalize_reusable_unit(
        source,
        IRNormalizationPolicy.PROMOTE_WRITTEN_INPUTS,
    )

    assert result.unit.kind is IRUnitKind.FUNCTION_BLOCK
    assert [
        item.direction
        for item in result.unit.parameters
        if item.name == "Val"
    ] == [IRDirection.OUTPUT]
    assert [item.code for item in result.changes] == [
        "input_promoted_to_output",
        "unit_promoted_to_function_block",
    ]
    assert not any(
        item.code == "write_to_input_parameter"
        for item in result.unit.diagnostics
    )


def test_normalized_str_capacity_emits_complete_canonical_iec():
    normalized = normalize_reusable_unit(
        _str_capacity(),
        IRNormalizationPolicy.PROMOTE_WRITTEN_INPUTS,
    ).unit

    result = emit_iec_st_unit(normalized)

    assert """\
VAR_OUTPUT
    EnableOut : BOOL;
    Val : DINT;
END_VAR
""" in result.text
    assert result.requirements == (
        IECRequirement.ARRAY_DIMENSION,
        IECRequirement.GENERIC_ARRAY_INTERFACE,
    )
    assert {item.code for item in result.diagnostics} == {
        "input_promoted_to_output",
        "unit_promoted_to_function_block",
    }
    assert result.complete
