from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.ir import (
    IRArrayDimension,
    IRAssignment,
    IRControllerObjectRead,
    IRControllerObjectIntent,
    IRControllerObjectWrite,
    IRDirection,
    IRIf,
    IRLiteral,
    IRLifecycle,
    IRReference,
    IRRoutineRole,
    IRUnitKind,
    IRUnsupportedStatement,
    IRWhile,
    IRWallClockRead,
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


def test_str_capacity_lowers_to_neutral_array_dimension_assignment():
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

    unit = lower_add_on_instruction(instruction, semantics)

    assert unit.kind is IRUnitKind.FUNCTION
    assert unit.source_vendor == "Jeremy Medders"
    assert unit.lifecycle == IRLifecycle(
        prescan_enabled=False,
        postscan_enabled=False,
        enable_in_false_enabled=False,
    )
    assert [
        (item.name, item.direction, item.dimensions)
        for item in unit.parameters
    ] == [
        ("EnableIn", IRDirection.INPUT, None),
        ("EnableOut", IRDirection.OUTPUT, None),
        ("Ref_Data", IRDirection.INOUT, "1"),
        ("Val", IRDirection.INPUT, None),
    ]
    assert unit.variables == ()
    assert [item.code for item in unit.diagnostics] == [
        "write_to_input_parameter"
    ]
    assert len(unit.routines) == 1
    routine = unit.routines[0]
    assert routine.source == instruction.routines["Logic"].structured_text
    assert routine.diagnostics == ()
    statement = routine.statements[0]
    assert isinstance(statement, IRAssignment)
    assert isinstance(statement.target, IRReference)
    assert statement.target.name == "Val"
    assert isinstance(statement.value, IRArrayDimension)
    assert statement.value.data_type == "DINT"
    assert isinstance(statement.value.array, IRReference)
    assert statement.value.array.name == "Ref_Data"
    assert isinstance(statement.value.dimension, IRLiteral)
    assert statement.value.dimension.lexical_value == "0"


def test_control_flow_lowers_to_typed_neutral_statements():
    document = parse_structured_text(
        "IF Enabled THEN Count := Count + 1; END_IF;"
        "WHILE Count < Limit DO Count := Count + 1; END_WHILE;"
    )
    semantics = analyze_semantics(
        document,
        SemanticContext(
            symbols=(
                SemanticSymbol("Enabled", SymbolKind.PARAMETER, "BOOL"),
                SemanticSymbol("Count", SymbolKind.LOCAL, "DINT"),
                SemanticSymbol("Limit", SymbolKind.PARAMETER, "DINT"),
            )
        ),
    )

    routine = lower_structured_text(semantics, routine_name="Logic")

    assert routine.diagnostics == ()
    assert isinstance(routine.statements[0], IRIf)
    assert isinstance(routine.statements[1], IRWhile)
    conditional = routine.statements[0]
    assert isinstance(conditional, IRIf)
    assert conditional.branches[0].condition.data_type == "BOOL"
    loop = routine.statements[1]
    assert isinstance(loop, IRWhile)
    assert loop.condition.data_type == "BOOL"


def test_unsupported_source_remains_explicit_in_ir():
    source = "CASE State OF 1: Out := TRUE; END_CASE;"
    semantics = analyze_semantics(
        parse_structured_text(source),
        SemanticContext(),
    )

    routine = lower_structured_text(semantics, routine_name="Logic")

    unsupported = [
        item
        for item in routine.statements
        if isinstance(item, IRUnsupportedStatement)
    ]
    assert [item.source for item in unsupported] == [
        "CASE",
        "State",
        "OF",
        "1:",
        "END_CASE;",
    ]
    assert semantics.document.reconstructed_source == source
    assert any(
        item.code == "unsupported_statement"
        for item in routine.diagnostics
    )


def test_scan_mode_routines_lower_with_explicit_lifecycle_roles():
    controller = next(
        L5XParser()
        .parse(DATA / "scan_mode_routines.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["LifecycleAOI"]
    report = analyze_structured_text_semantics(controller)

    unit = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:LifecycleAOI"
        },
    )

    assert [(item.name, item.role) for item in unit.routines] == [
        ("Logic", IRRoutineRole.PRIMARY),
        ("Prescan", IRRoutineRole.PRESCAN),
        ("Postscan", IRRoutineRole.POSTSCAN),
        ("EnableInFalse", IRRoutineRole.ENABLE_IN_FALSE),
    ]


def test_lifecycle_name_is_resolved_when_studio_exports_it_under_routines():
    controller = next(
        L5XParser()
        .parse(DATA / "lifecycle_in_routines.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["LifecycleInRoutines"]
    report = analyze_structured_text_semantics(controller)

    unit = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:LifecycleInRoutines"
        },
    )

    assert instruction.scan_mode_routines == {}
    assert [(item.name, item.role) for item in unit.routines] == [
        ("Logic", IRRoutineRole.PRIMARY),
        ("Prescan", IRRoutineRole.PRESCAN),
    ]
    assert any(
        item.code == "lifecycle_routine_in_routines_container"
        for item in unit.diagnostics
    )


def test_wall_clock_gsv_lowers_to_unit_aware_neutral_operation():
    controller = next(
        L5XParser()
        .parse(DATA / "rtc_pulse.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["RTC_PulseGen"]
    report = analyze_structured_text_semantics(controller)
    unit = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:RTC_PulseGen"
        },
    )

    statement = unit.routines[0].statements[0]
    assert isinstance(statement, IRWallClockRead)
    assert isinstance(statement.destination, IRReference)
    assert statement.destination.name == "TNow"
    assert statement.timestamp_unit == "microseconds"
    interval = next(
        item for item in unit.parameters if item.name == "Inp_Interval"
    )
    assert interval.default_value == 1000
    assert interval.default_lexical_value == "1000"


def test_module_gsv_and_ssv_lower_to_structured_controller_services():
    controller = next(
        L5XParser()
        .parse(DATA / "controller_object_services.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["ModuleServices"]
    report = analyze_structured_text_semantics(controller)
    unit = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:ModuleServices"
        },
    )

    read, write = unit.routines[0].statements
    assert isinstance(read, IRControllerObjectRead)
    assert (
        read.object_class,
        read.instance,
        read.attribute,
    ) == ("Module", "Ref_Module", "Mode")
    assert isinstance(read.destination, IRReference)
    assert read.destination.name == "Value"
    assert read.intent is IRControllerObjectIntent.OPERATING_MODE
    assert isinstance(write, IRControllerObjectWrite)
    assert (
        write.object_class,
        write.instance,
        write.attribute,
    ) == ("Module", "Ref_Module", "Mode")
    assert isinstance(write.value, IRReference)
    assert write.value.name == "ModeSet"
    assert write.intent is IRControllerObjectIntent.SET_INHIBITED
    assert unit.routines[0].diagnostics == ()
