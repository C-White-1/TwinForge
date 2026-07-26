from dataclasses import replace
from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.exporters import emit_codesys_st_unit
from twinforge.ir import (
    IRAssignment,
    IRIf,
    IRLifecycle,
    IRNormalizationPolicy,
    IRReference,
    apply_aoi_execution_semantics,
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
    analysis = analyze_structured_text_semantics(controller)
    lowered = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in analysis.routines
            if finding.owner == "AOI:Str_Capacity"
        },
    )
    return normalize_reusable_unit(
        lowered,
        IRNormalizationPolicy.PROMOTE_WRITTEN_INPUTS,
    ).unit


def test_lowering_preserves_disabled_lifecycle_flags():
    unit = _str_capacity()

    assert unit.lifecycle == IRLifecycle(
        prescan_enabled=False,
        postscan_enabled=False,
        enable_in_false_enabled=False,
    )


def test_applies_default_enable_propagation_and_main_guard():
    result = apply_aoi_execution_semantics(_str_capacity())
    statements = result.routines[0].statements

    assert isinstance(statements[0], IRAssignment)
    assert isinstance(statements[0].target, IRReference)
    assert statements[0].target.name == "EnableOut"
    assert isinstance(statements[0].value, IRReference)
    assert statements[0].value.name == "EnableIn"
    assert isinstance(statements[1], IRIf)
    assert isinstance(statements[1].branches[0].condition, IRReference)
    assert statements[1].branches[0].condition.name == "EnableIn"
    assert statements[1].else_statements == ()
    assert [item.code for item in result.diagnostics[-3:]] == [
        "default_enable_out_synthesized",
        "main_routine_guarded_by_enable_in",
        "aoi_enable_semantics_applied",
    ]


def test_execution_transformation_is_idempotent():
    first = apply_aoi_execution_semantics(_str_capacity())

    second = apply_aoi_execution_semantics(first)

    assert second is first


def test_disabled_lifecycle_modes_emit_no_calls_or_blockers():
    result = emit_codesys_st_unit(
        apply_aoi_execution_semantics(_str_capacity())
    )

    assert """\
EnableOut := EnableIn;
IF EnableIn THEN
    Val := ((UPPER_BOUND(Ref_Data, (0 + 1)) - LOWER_BOUND(Ref_Data, (0 + 1))) + 1);
END_IF;
""" in result.text
    assert not any(
        item.code.endswith("_mapping_required")
        for item in result.diagnostics
    )
    assert result.complete


def test_enabled_unmapped_lifecycle_mode_blocks_complete_export():
    source = _str_capacity()
    source = replace(
        source,
        lifecycle=replace(source.lifecycle, prescan_enabled=True),
    )

    result = emit_codesys_st_unit(
        apply_aoi_execution_semantics(source)
    )

    assert any(
        item.code == "prescan_mapping_required"
        for item in result.diagnostics
    )
    assert not result.complete
