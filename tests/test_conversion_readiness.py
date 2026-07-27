from twinforge.analysis import (
    AOIPortability,
    AOIPortabilityFinding,
    ConversionDisposition,
    CyclicIOContract,
    CyclicIOImage,
    DeviceDiagnosticReport,
    BehaviourMatch,
    PLCopenBehaviourAssessment,
    PLCopenBehaviourModel,
    RecommendedPOU,
    build_conversion_readiness_report,
)
from twinforge.exporters import ConversionReadinessMarkdownExporter


def _finding() -> AOIPortabilityFinding:
    return AOIPortabilityFinding(
        name="DriveAOI",
        disposition=AOIPortability.ADAPTER_REQUIRED,
        recommended_pou=RecommendedPOU.FUNCTION_BLOCK,
        plcopen_behaviour=PLCopenBehaviourAssessment(
            model=PLCopenBehaviourModel.NONE,
            match=BehaviourMatch.NONE,
            parameter_mapping=(),
            missing_parameters=(),
            wrapper_recommended=False,
            extensions=(),
            evidence=(),
        ),
        stateful=True,
        lifecycle_hooks=("prescan",),
        dependencies=(
            "AddOnInstructionDefinition:RTC_PulseGen",
            "DataType:ST_Dvc_PF525",
        ),
        unresolved_dependencies=(),
        referenced_data_types=("MESSAGE", "MODULE"),
        structured_text_calls=("COP", "MSG", "SIZE", "SWPB", "TONR"),
        rockwell_services=("MSG",),
        rockwell_data_types=("MESSAGE", "MODULE"),
        runtime_requirements=(),
        unanalyzed_routines=(),
        reasons=(),
    )


def _cyclic() -> CyclicIOContract:
    return CyclicIOContract(
        implementation_name="DriveAOI",
        protocol="EtherNet/IP",
        requested_packet_interval_microseconds=10_000,
        unicast=True,
        input_image=CyclicIOImage(
            role="status",
            parameter_name="Input",
            parameter_data_type="InputType",
            connection_point=1,
            configured_size_bytes=8,
            copied_size_bytes=8,
            local_path="Local.Input",
            fields=(),
        ),
        output_image=CyclicIOImage(
            role="command",
            parameter_name="Output",
            parameter_data_type="OutputType",
            connection_point=2,
            configured_size_bytes=4,
            copied_size_bytes=4,
            local_path="Local.Output",
            fields=(),
        ),
    )


def _diagnostics() -> DeviceDiagnosticReport:
    return DeviceDiagnosticReport(
        device_name="Drive",
        implementation_name="DriveAOI",
        indicators=(),
        policies=(),
        fault_history=(),
        commands=(),
        limitations=(),
    )


def test_classifies_conversion_work_and_dependencies():
    report = build_conversion_readiness_report(
        _finding(),
        _cyclic(),
        _diagnostics(),
    )

    assert report.items[0].disposition is (
        ConversionDisposition.DIRECT_PORTABLE
    )
    assert report.items[1].disposition is (
        ConversionDisposition.TYPE_ADAPTATION
    )
    assert report.dependencies[0].name == "RTC_PulseGen"
    assert report.dependencies[0].disposition is (
        ConversionDisposition.TARGET_ADAPTER
    )


def test_exports_readiness_matrix_as_markdown():
    report = build_conversion_readiness_report(
        _finding(),
        _cyclic(),
        _diagnostics(),
    )

    result = ConversionReadinessMarkdownExporter().export(report)

    assert "# DriveAOI conversion-readiness report" in result
    assert "- Unresolved dependencies: 0" in result
    assert "| Core command and speed logic | `direct_portable`" in result
    assert "## Architecture boundary" in result
