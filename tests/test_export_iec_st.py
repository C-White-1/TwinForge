from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.exporters import (
    IECRequirement,
    emit_iec_st_routine,
    emit_iec_st_unit,
)
from twinforge.ir import (
    IRReusableUnit,
    IRRoutine,
    IRUnitKind,
    IRVariable,
    lower_add_on_instruction,
    lower_structured_text,
)
from twinforge.parsers import L5XParser
from twinforge.structured_text import (
    SemanticContext,
    SemanticSymbol,
    SymbolKind,
    analyze_semantics,
    parse_structured_text,
)


DATA = Path(__file__).parent / "data/aoi"


def _str_capacity():
    controller = next(
        L5XParser()
        .parse(DATA / "Str_Capacity_AOI.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["Str_Capacity"]
    report = analyze_structured_text_semantics(controller)
    semantics = {
        finding.routine: finding.semantics
        for finding in report.routines
        if finding.owner == "AOI:Str_Capacity"
    }
    return lower_add_on_instruction(instruction, semantics)


def test_str_capacity_emits_canonical_iec_with_explicit_requirements():
    result = emit_iec_st_unit(_str_capacity())

    assert result.text == """\
FUNCTION_BLOCK Str_Capacity
VAR_INPUT
    EnableIn : BOOL;
    Val : DINT;
END_VAR
VAR_OUTPUT
    EnableOut : BOOL;
END_VAR
VAR_IN_OUT
    Ref_Data : ARRAY[*] OF SINT;
END_VAR
Val := TF_ArrayDimension(Ref_Data, 0);
END_FUNCTION_BLOCK
"""
    assert result.requirements == (
        IECRequirement.ARRAY_DIMENSION,
        IECRequirement.GENERIC_ARRAY_INTERFACE,
    )
    assert {item.code for item in result.diagnostics} == {
        "implementation_shape_adjusted",
        "write_to_input_parameter",
    }
    assert not result.complete


def test_portable_control_flow_emits_without_target_requirements():
    semantics = analyze_semantics(
        parse_structured_text(
            "IF Enabled THEN Count := Count + 1; END_IF;"
        ),
        SemanticContext(
            symbols=(
                SemanticSymbol("Enabled", SymbolKind.PARAMETER, "BOOL"),
                SemanticSymbol("Count", SymbolKind.LOCAL, "DINT"),
            )
        ),
    )
    routine = lower_structured_text(semantics, routine_name="Logic")

    result = emit_iec_st_routine(routine)

    assert result.text == """\
IF Enabled THEN
    Count := (Count + 1);
END_IF;
"""
    assert result.requirements == ()
    assert result.diagnostics == ()
    assert result.complete


def test_unsupported_ir_is_visible_and_blocks_completion():
    semantics = analyze_semantics(
        parse_structured_text("CASE State OF 1: Out := TRUE; END_CASE;"),
        SemanticContext(),
    )

    result = emit_iec_st_routine(
        lower_structured_text(semantics, routine_name="Logic")
    )

    assert "TwinForge unsupported" in result.text
    assert "TF_UNSUPPORTED()" in result.text
    assert not result.complete


def test_multiple_routines_require_lifecycle_mapping():
    unit = IRReusableUnit(
        name="Stateful",
        kind=IRUnitKind.FUNCTION_BLOCK,
        parameters=(),
        variables=(IRVariable("State", "DINT"),),
        routines=(
            IRRoutine("Logic", "ST", "", ()),
            IRRoutine("Prescan", "ST", "", ()),
        ),
    )

    result = emit_iec_st_unit(unit)

    assert "VAR\n    State : DINT;\nEND_VAR" in result.text
    assert any(
        item.code == "multiple_routines_require_lifecycle_mapping"
        for item in result.diagnostics
    )
    assert not result.complete
