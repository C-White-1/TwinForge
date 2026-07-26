from pathlib import Path

from twinforge.analysis import (
    AOIPortability,
    RecommendedPOU,
    RuntimeCapability,
    RuntimeRequirement,
    analyze_aoi_portability,
    evaluate_runtime_compatibility,
    extract_structured_text_calls,
)
from twinforge.model import (
    AddOnInstruction,
    AddOnInstructionParameter,
    Controller,
    Identity,
    Routine,
    StructuredTextLine,
)
from twinforge.parsers import L5XParser


DATA = Path(__file__).parent / "data/aoi"


def _parse_controller(name: str) -> Controller:
    plant = L5XParser().parse(DATA / name, report_mode=None)
    return next(plant.iter_controllers())


def test_str_capacity_is_a_stateless_portable_function_candidate():
    report = analyze_aoi_portability(
        _parse_controller("Str_Capacity_AOI.L5X")
    )

    finding = report.findings[0]
    assert finding.name == "Str_Capacity"
    assert finding.disposition is AOIPortability.PORTABLE_CANDIDATE
    assert finding.recommended_pou is RecommendedPOU.FUNCTION
    assert finding.structured_text_calls == ("SIZE",)


def test_local_state_and_lifecycle_select_function_block():
    report = analyze_aoi_portability(
        _parse_controller("dependencies_and_locals.L5X")
    )

    finding = next(item for item in report.findings if item.name == "MainAOI")
    assert finding.disposition is AOIPortability.PORTABLE_CANDIDATE
    assert finding.recommended_pou is RecommendedPOU.FUNCTION_BLOCK
    assert finding.stateful
    assert finding.unresolved_dependencies == ()


def test_rockwell_service_and_datatype_require_adapter():
    controller = Controller(name="Example", identity=Identity())
    instruction = AddOnInstruction(name="DriveMessage")
    instruction.add_parameter(
        AddOnInstructionParameter(name="Request", data_type="MESSAGE")
    )
    instruction.add_routine(
        Routine(
            name="Logic",
            language="ST",
            structured_text_lines=[
                StructuredTextLine(text="MSG(Request);"),
            ],
        )
    )
    controller.add_add_on_instruction(instruction)

    finding = analyze_aoi_portability(controller).findings[0]
    assert finding.disposition is AOIPortability.ADAPTER_REQUIRED
    assert finding.rockwell_services == ("MSG",)
    assert finding.rockwell_data_types == ("MESSAGE",)
    assert finding.runtime_requirements == (
        RuntimeRequirement(
            RuntimeCapability.EXPLICIT_MESSAGING,
            ("data_type:MESSAGE", "service:MSG"),
        ),
    )


def test_call_extraction_ignores_control_words_and_comments():
    calls = extract_structured_text_calls(
        "IF Ready() THEN\n(* GSV(Hidden); *)\nDoWork(); // MSG(X)\nEND_IF;"
    )

    assert calls == ("DoWork", "Ready")


def test_runtime_provider_reports_missing_contracts():
    class ExampleRuntime:
        runtime_name = "Example"
        capabilities = frozenset({RuntimeCapability.MODULE_REFERENCE})

    compatibility = evaluate_runtime_compatibility(
        (
            RuntimeRequirement(
                RuntimeCapability.MODULE_REFERENCE, ("data_type:MODULE",)
            ),
            RuntimeRequirement(
                RuntimeCapability.EXPLICIT_MESSAGING, ("service:MSG",)
            ),
        ),
        ExampleRuntime(),
    )

    assert not compatibility.compatible
    assert compatibility.missing == (
        RuntimeCapability.EXPLICIT_MESSAGING,
    )


def test_wall_clock_gsv_has_a_specific_runtime_requirement():
    controller = Controller(name="Example", identity=Identity())
    instruction = AddOnInstruction(name="Pulse")
    instruction.add_routine(
        Routine(
            name="Logic",
            language="ST",
            structured_text_lines=[
                StructuredTextLine(
                    text="GSV(WallClockTime, , CurrentValue, TNow);"
                ),
            ],
        )
    )
    controller.add_add_on_instruction(instruction)

    requirements = analyze_aoi_portability(
        controller
    ).findings[0].runtime_requirements

    assert requirements == (
        RuntimeRequirement(
            RuntimeCapability.WALL_CLOCK_READ,
            ("service:GSV(WallClockTime)",),
        ),
    )
