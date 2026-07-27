from twinforge.analysis import (
    CyclicIOContract,
    CyclicIOImage,
    DeviceDiagnosticReport,
    build_device_functional_description,
)
from twinforge.exporters import FunctionalDescriptionMarkdownExporter
from twinforge.model import (
    AddOnInstruction,
    AddOnInstructionParameter,
    Device,
    Routine,
    StructuredTextLine,
)


def _implementation() -> AddOnInstruction:
    aoi = AddOnInstruction(name="DriveAOI")
    for name in (
        "Sts_Program",
        "Sts_Operator",
        "Sts_External",
        "Sts_Override",
        "Sts_Maintenance",
        "Sts_Local",
        "Sts_Disabled",
    ):
        aoi.add_parameter(
            AddOnInstructionParameter(name=name, usage="Output")
        )
    aoi.add_routine(
        Routine(
            name="Logic",
            language="ST",
            structured_text_lines=[
                StructuredTextLine(text="PermOK := Inp_PermOK;"),
                StructuredTextLine(text="IntlkOK := Inp_IntlkOK;"),
                StructuredTextLine(text="RefSpeed := PSet_Speed;"),
            ],
        )
    )
    return aoi


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


def test_builds_modes_and_behavior_sections():
    device = Device(
        name="Drive",
        model="PowerFlex 525",
    )

    report = build_device_functional_description(
        device,
        _implementation(),
        _cyclic(),
        _diagnostics(),
    )

    assert len(report.modes) == 6
    assert report.modes[0].name == "Program"
    assert report.behaviors[1].name == "Permissives and interlocks"


def test_exports_functional_description_as_markdown():
    device = Device(
        name="Drive",
        model="PowerFlex 525",
    )
    report = build_device_functional_description(
        device,
        _implementation(),
        _cyclic(),
        _diagnostics(),
    )

    result = FunctionalDescriptionMarkdownExporter().export(report)

    assert "# Drive functional description" in result
    assert "- Cyclic protocol: EtherNet/IP, RPI 10 ms" in result
    assert "## Command-source modes" in result
    assert "PF525-QA-020" in result
