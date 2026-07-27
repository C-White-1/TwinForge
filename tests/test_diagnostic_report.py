from twinforge.analysis import build_device_diagnostic_report
from twinforge.exporters import DeviceDiagnosticMarkdownExporter
from twinforge.knowledge.powerflex525_parameters import (
    PowerFlex525ParameterCatalogue,
)
from twinforge.model import (
    AddOnInstruction,
    AddOnInstructionParameter,
    Device,
    DeviceParameterValueEvidence,
    ObservedParameterAccess,
    Routine,
    StructuredTextLine,
)


def _observed(number: int, value: str | None = None):
    definition = PowerFlex525ParameterCatalogue().definition(number)
    assert definition is not None
    return ObservedParameterAccess(
        number=number,
        definition=definition,
        configured_value=(
            DeviceParameterValueEvidence(
                lexical_value=value,
                source=f"Drive.Cfg_{definition.name.replace(' ', '')}",
            )
            if value is not None
            else None
        ),
    )


def _implementation() -> AddOnInstruction:
    aoi = AddOnInstruction(name="DriveAOI")
    for name, usage, alias in (
        ("Sts_Fault", "Output", "Local.DataIn.Fault"),
        ("Sts_CommLoss", "Output", "Module.Sts_Disconnected"),
        ("Sts_ResetReady", "Output", "Local.Params.ResetReady"),
        ("PCmd_Reset", "Input", "PCmd.5"),
        ("OCmd_Reset", "Input", "OCmd.5"),
        ("PCmd_ClearFaultBuffer", "Input", "PCmd.6"),
    ):
        aoi.add_parameter(
            AddOnInstructionParameter(
                name=name,
                usage=usage,
                alias_for=alias,
                visible=True,
            )
        )
    aoi.add_routine(
        Routine(
            name="Logic",
            language="ST",
            structured_text_lines=[
                StructuredTextLine(
                    text=(
                        "Local.DataOut.ClearFault := PCmd_Reset "
                        "OR OCmd_Reset;"
                    )
                ),
                StructuredTextLine(
                    text="Local.Params.FaultClear.SP := 2;"
                ),
            ],
        )
    )
    return aoi


def test_builds_separated_diagnostic_contract():
    device = Device(name="Drive")
    device.observed_parameters = [
        _observed(143, "0"),
        _observed(7),
        _observed(631),
        _observed(641),
        _observed(651),
    ]

    report = build_device_diagnostic_report(device, _implementation())

    assert report.policies[0].configured_label == "Fault"
    assert report.fault_history[0].code_parameter == "b007"
    assert report.fault_history[0].frequency_parameter == "F631"
    assert report.fault_history[0].current_parameter == "F641"
    assert report.fault_history[0].bus_voltage_parameter == "F651"
    assert report.commands[0].source == "PCmd_Reset, OCmd_Reset"


def test_exports_diagnostic_report_as_markdown():
    device = Device(name="Drive")
    device.observed_parameters = [_observed(143, "0"), _observed(7)]

    report = build_device_diagnostic_report(device, _implementation())
    result = DeviceDiagnosticMarkdownExporter().export(report)

    assert "## Live diagnostic contract" in result
    assert "| `C143` EN Comm Flt Actn" in result
    assert "`0` (Fault)" in result
    assert "## Important boundaries" in result
