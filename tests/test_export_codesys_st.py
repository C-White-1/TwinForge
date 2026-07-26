from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.exporters import IECRequirement, emit_codesys_st_unit
from twinforge.ir import (
    IRNormalizationPolicy,
    IRDirection,
    IRParameter,
    IRReusableUnit,
    IRRoutine,
    IRUnitKind,
    lower_add_on_instruction,
    normalize_reusable_unit,
)
from twinforge.parsers import L5XParser


DATA = Path(__file__).parent / "data/aoi"


def _normalized_str_capacity():
    controller = next(
        L5XParser()
        .parse(DATA / "Str_Capacity_AOI.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["Str_Capacity"]
    report = analyze_structured_text_semantics(controller)
    lowered = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:Str_Capacity"
        },
    )
    return normalize_reusable_unit(
        lowered,
        IRNormalizationPolicy.PROMOTE_WRITTEN_INPUTS,
    ).unit


def test_codesys_maps_size_to_array_bounds_and_resolves_requirements():
    result = emit_codesys_st_unit(_normalized_str_capacity())

    assert (
        "Val := ((UPPER_BOUND(Ref_Data, (0 + 1)) - "
        "LOWER_BOUND(Ref_Data, (0 + 1))) + 1);"
    ) in result.text
    assert "Ref_Data : ARRAY[*] OF SINT;" in result.text
    assert "TF_ArrayDimension" not in result.text
    assert result.requirements == ()
    assert result.complete


def test_codesys_output_retains_normalization_audit_diagnostics():
    result = emit_codesys_st_unit(_normalized_str_capacity())

    assert {item.code for item in result.diagnostics} == {
        "input_promoted_to_output",
        "unit_promoted_to_function_block",
    }


def test_codesys_does_not_claim_generic_output_array_support():
    unit = IRReusableUnit(
        name="GenericOutput",
        kind=IRUnitKind.FUNCTION_BLOCK,
        parameters=(
            IRParameter(
                name="Values",
                direction=IRDirection.OUTPUT,
                data_type="DINT",
                dimensions="0",
                generic_dimensions=True,
            ),
        ),
        variables=(),
        routines=(
            IRRoutine(
                name="Logic",
                source_language="ST",
                source="",
                statements=(),
            ),
        ),
    )

    result = emit_codesys_st_unit(unit)

    assert result.requirements == (
        IECRequirement.GENERIC_ARRAY_INTERFACE,
    )
