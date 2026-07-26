from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.parsers import L5XParser
from twinforge.structured_text import (
    AccessStatus,
    CallKind,
    CallParameter,
    CallRule,
    NeutralOperationKind,
    ReferenceStatus,
    SemanticContext,
    SemanticSymbol,
    SemanticType,
    SemanticTypeMember,
    SymbolKind,
    TypeStatus,
    TypeCompatibility,
    TypeConversionPolicy,
    analyze_semantics,
    parse_structured_text,
)


DATA = Path(__file__).parent / "data/aoi"


def test_generic_semantics_resolve_symbols_and_preserve_unknown_calls():
    document = parse_structured_text(
        "Result := Source + 1; Mystery(Result);"
    )
    semantics = analyze_semantics(
        document,
        SemanticContext(
            symbols=(
                SemanticSymbol("Result", SymbolKind.LOCAL, "DINT"),
                SemanticSymbol("Source", SymbolKind.PARAMETER, "DINT"),
            )
        ),
    )

    assert [item.status for item in semantics.references] == [
        ReferenceStatus.RESOLVED,
        ReferenceStatus.RESOLVED,
        ReferenceStatus.RESOLVED,
    ]
    assert semantics.calls[0].kind is CallKind.UNKNOWN
    assert semantics.diagnostics[0].code == "unknown_call"
    assert semantics.operations[0].kind is NeutralOperationKind.ASSIGN
    assert semantics.document.reconstructed_source == document.source


def test_declarative_call_rule_can_exclude_opaque_source_operands():
    semantics = analyze_semantics(
        parse_structured_text(
            "GSV(WallClockTime, , CurrentValue, Destination);"
        ),
        SemanticContext(
            symbols=(
                SemanticSymbol(
                    "Destination",
                    SymbolKind.LOCAL,
                    "LINT",
                ),
            ),
            call_rules=(
                CallRule(
                    "GSV",
                    CallKind.CONTROLLER_OBJECT_READ,
                    "controller_object_read",
                    vendor="Rockwell Automation",
                    opaque_argument_indices=frozenset({0, 1, 2}),
                ),
            ),
        ),
    )

    assert semantics.calls[0].kind is CallKind.CONTROLLER_OBJECT_READ
    assert [item.name for item in semantics.references] == ["Destination"]
    assert semantics.diagnostics == ()


def test_controller_adapter_resolves_str_capacity_aoi_scope_and_size():
    plant = L5XParser().parse(
        DATA / "Str_Capacity_AOI.L5X",
        report_mode=None,
    )
    report = analyze_structured_text_semantics(
        next(plant.iter_controllers())
    )

    assert len(report.routines) == 1
    assert report.resolved_references == 2
    assert report.unresolved_references == 0
    assert report.unknown_calls == 0
    assert report.invalid_accesses == 0
    assert report.invalid_signatures == 0
    assert "Assignment compatibility:" in report.render_text()
    assert report.routines[0].semantics.type_definitions
    finding = report.routines[0]
    assert finding.semantics.calls[0].kind is (
        CallKind.ARRAY_DIMENSION_QUERY
    )
    assert finding.semantics.calls[0].neutral_name == (
        "array_dimension_query"
    )
    assert finding.semantics.document.reconstructed_source == (
        finding.semantics.document.source
    )
    assert "Resolved references: 2" in report.render_text()


def test_captured_member_paths_and_array_access_are_validated():
    semantics = analyze_semantics(
        parse_structured_text(
            "Motor.Alarm.Enabled := Samples[Index] > 1.0;"
        ),
        SemanticContext(
            symbols=(
                SemanticSymbol(
                    "Motor",
                    SymbolKind.CONTROLLER_TAG,
                    "MotorConfig",
                ),
                SemanticSymbol(
                    "Samples",
                    SymbolKind.LOCAL,
                    "REAL",
                    dimensions="10",
                ),
                SemanticSymbol("Index", SymbolKind.LOCAL, "DINT"),
            ),
            types=(
                SemanticType(
                    "MotorConfig",
                    (
                        SemanticTypeMember(
                            "Alarm",
                            "AlarmConfig",
                            "0",
                        ),
                    ),
                ),
                SemanticType(
                    "AlarmConfig",
                    (SemanticTypeMember("Enabled", "BOOL", "0"),),
                ),
            ),
        ),
    )

    assert [item.status for item in semantics.accesses] == [
        AccessStatus.RESOLVED,
        AccessStatus.RESOLVED,
        AccessStatus.RESOLVED,
    ]
    assert semantics.accesses[1].data_type == "BOOL"
    assert any(
        item.data_type == "BOOL" and item.status is TypeStatus.KNOWN
        for item in semantics.expression_types
    )
    assert semantics.diagnostics == ()


def test_invalid_captured_member_and_call_arity_are_diagnostics():
    semantics = analyze_semantics(
        parse_structured_text("Motor.Missing := ABS(One, Two);"),
        SemanticContext(
            symbols=(
                SemanticSymbol(
                    "Motor",
                    SymbolKind.CONTROLLER_TAG,
                    "MotorConfig",
                ),
                SemanticSymbol("One", SymbolKind.LOCAL, "DINT"),
                SemanticSymbol("Two", SymbolKind.LOCAL, "DINT"),
            ),
            types=(
                SemanticType(
                    "MotorConfig",
                    (SemanticTypeMember("Speed", "REAL", "0"),),
                ),
            ),
            call_rules=(
                CallRule(
                    "ABS",
                    CallKind.ABSOLUTE_VALUE,
                    "absolute_value",
                    minimum_arguments=1,
                    maximum_arguments=1,
                    result_from_argument=0,
                ),
            ),
        ),
    )

    assert semantics.accesses[0].status is AccessStatus.INVALID
    assert semantics.calls[0].signature_valid is False
    assert {item.code for item in semantics.diagnostics} == {
        "invalid_member",
        "invalid_argument_count",
    }


def test_external_member_definition_remains_unverified():
    semantics = analyze_semantics(
        parse_structured_text("Timer.DN := TRUE;"),
        SemanticContext(
            symbols=(
                SemanticSymbol("Timer", SymbolKind.LOCAL, "TIMER"),
            )
        ),
    )

    assert semantics.accesses[0].status is AccessStatus.UNVERIFIED
    assert semantics.diagnostics == ()


def test_partial_type_keeps_unknown_members_unverified():
    semantics = analyze_semantics(
        parse_structured_text("Message.FutureMember := 1;"),
        SemanticContext(
            symbols=(
                SemanticSymbol("Message", SymbolKind.LOCAL, "MESSAGE"),
            ),
            types=(
                SemanticType(
                    "MESSAGE",
                    (SemanticTypeMember("DN", "BOOL", "0"),),
                    complete=False,
                ),
            ),
        ),
    )

    assert semantics.accesses[0].status is AccessStatus.UNVERIFIED
    assert semantics.diagnostics == ()


def test_assignment_policy_distinguishes_implicit_and_incompatible_types():
    semantics = analyze_semantics(
        parse_structured_text("RealValue := Count; Flag := Count;"),
        SemanticContext(
            symbols=(
                SemanticSymbol("RealValue", SymbolKind.LOCAL, "REAL"),
                SemanticSymbol("Count", SymbolKind.LOCAL, "DINT"),
                SemanticSymbol("Flag", SymbolKind.LOCAL, "BOOL"),
            ),
            conversion_policy=TypeConversionPolicy(
                implicit_numeric=True,
                bit_bool_equivalent=True,
            ),
        ),
    )

    assert [item.compatibility for item in semantics.assignments] == [
        TypeCompatibility.IMPLICIT,
        TypeCompatibility.INCOMPATIBLE,
    ]
    assert semantics.diagnostics[-1].code == "incompatible_assignment"


def test_aoi_style_contract_binds_instance_and_required_parameters():
    semantics = analyze_semantics(
        parse_structured_text(
            "Scale(ScaleInstance, InputValue, OutputValue);"
        ),
        SemanticContext(
            symbols=(
                SemanticSymbol(
                    "ScaleInstance",
                    SymbolKind.LOCAL,
                    "Scale",
                ),
                SemanticSymbol("InputValue", SymbolKind.LOCAL, "DINT"),
                SemanticSymbol("OutputValue", SymbolKind.LOCAL, "REAL"),
            ),
            call_rules=(
                CallRule(
                    "Scale",
                    CallKind.USER_DEFINED_INSTRUCTION,
                    "Scale",
                    minimum_arguments=3,
                    maximum_arguments=3,
                    instance_data_type="Scale",
                    parameters=(
                        CallParameter("Input", "REAL", "Input"),
                        CallParameter("Output", "REAL", "InOut"),
                    ),
                ),
            ),
            conversion_policy=TypeConversionPolicy(
                implicit_numeric=True,
            ),
        ),
    )

    call = semantics.calls[0]
    assert call.signature_valid is True
    assert [item.parameter_name for item in call.bindings] == [
        "@instance",
        "Input",
        "Output",
    ]
    assert [item.compatibility for item in call.bindings] == [
        TypeCompatibility.EXACT,
        TypeCompatibility.IMPLICIT,
        TypeCompatibility.EXACT,
    ]
    assert semantics.diagnostics == ()


def test_output_binding_rejects_a_literal():
    semantics = analyze_semantics(
        parse_structured_text("WriteResult(1);"),
        SemanticContext(
            call_rules=(
                CallRule(
                    "WriteResult",
                    CallKind.USER_DEFINED_INSTRUCTION,
                    "WriteResult",
                    minimum_arguments=1,
                    maximum_arguments=1,
                    parameters=(
                        CallParameter("Result", "DINT", "Output"),
                    ),
                ),
            ),
        ),
    )

    assert semantics.calls[0].bindings[0].compatibility is (
        TypeCompatibility.EXACT
    )
    assert semantics.diagnostics[0].code == (
        "non_assignable_output_argument"
    )
