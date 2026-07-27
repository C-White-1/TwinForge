import csv
from io import StringIO

from twinforge.analysis import build_parameter_setpoint_report
from twinforge.exporters import (
    ParameterReportCSVExporter,
    ParameterReportMarkdownExporter,
)
from twinforge.knowledge.powerflex525_parameters import (
    PowerFlex525ParameterCatalogue,
)
from twinforge.model import (
    Device,
    DeviceParameterValueEvidence,
    ObservedParameterAccess,
)


def _device() -> Device:
    definition = PowerFlex525ParameterCatalogue().definition(34)
    assert definition is not None
    device = Device(name="Drive")
    device.observed_parameters = [
        ObservedParameterAccess(
            number=34,
            code=definition.code,
            group_name=definition.group_name,
            display_name=definition.name,
            reference=definition.reference,
            definition=definition,
            observed_read=True,
            observed_write=True,
            read_buffer_indices=(13,),
            evidence=("Ref_MsgData[13] := 34;",),
            configured_value=DeviceParameterValueEvidence(
                lexical_value="2.5",
                source="Dvc.Cfg_MotorNPFLA",
                data_type="REAL",
                radix="Float",
            ),
        )
    ]
    return device


def test_builds_report_without_inventing_offline_or_runtime_values():
    report = build_parameter_setpoint_report(_device())

    assert report.device_name == "Drive"
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.code == "P034"
    assert entry.engineering_unit == "A"
    assert entry.minimum == "0.1"
    assert entry.maximum == "Drive Rated Amps × 2"
    assert entry.configured_value == "2.5"
    assert entry.configured_value_source == "Dvc.Cfg_MotorNPFLA"
    assert entry.runtime_value is None
    assert entry.runtime_value_source is None


def test_exports_parameter_report_as_markdown():
    report = build_parameter_setpoint_report(_device())

    result = ParameterReportMarkdownExporter().export(report)

    assert "Configured values are shown only when recoverable" in result
    assert "- Configured-value evidence: 1/1 parameters" in result
    assert "- Runtime-value evidence: 0/1 parameters" in result
    assert "- Interpreted configured values: 0/1" in result
    assert "- Mechanically verified configured values: 0/1" in result
    assert "- Configuration assessment exceptions: 0" in result
    assert "- Parameters with QA advisories: 0" in result
    assert "- Parameters with high-severity advisories: 0" in result
    assert (
        "| P034 | Motor NP FLA | Basic Program | 2.5 | — "
        "| Not automatically verifiable | — | — | A "
        "| 0.1 to Drive Rated Amps × 2 | Based on Drive Rating "
        "| read/write | no | — |"
    ) in result


def test_exports_parameter_report_as_csv():
    report = build_parameter_setpoint_report(_device())

    result = ParameterReportCSVExporter().export(report)
    rows = list(csv.DictReader(StringIO(result)))

    assert len(rows) == 1
    assert rows[0]["Code"] == "P034"
    assert rows[0]["ConfiguredValue"] == "2.5"
    assert rows[0]["ConfiguredValueLabel"] == ""
    assert (
        rows[0]["ConfiguredValueAssessment"]
        == "Not automatically verifiable"
    )
    assert rows[0]["ConfiguredValueSource"] == "Dvc.Cfg_MotorNPFLA"
    assert rows[0]["ConfigurationNote"] == ""
    assert rows[0]["RuntimeValue"] == ""
    assert rows[0]["EngineeringUnit"] == "A"
    assert rows[0]["ObservedRead"] == "yes"
    assert rows[0]["ObservedWrite"] == "yes"
    assert rows[0]["ChangeRequiresStop"] == "no"
    assert rows[0]["AdvisoryCodes"] == ""
    assert rows[0]["Evidence"] == "Ref_MsgData[13] := 34;"


def test_interprets_configured_enumerated_value():
    definition = PowerFlex525ParameterCatalogue().definition(38)
    assert definition is not None
    device = Device(name="Drive")
    device.observed_parameters = [
        ObservedParameterAccess(
            number=38,
            code=definition.code,
            display_name=definition.name,
            definition=definition,
            configured_value=DeviceParameterValueEvidence(
                lexical_value="3.0",
                source="Dvc.Cfg_VoltageClass",
            ),
        )
    ]

    report = build_parameter_setpoint_report(device)

    assert report.entries[0].configured_value == "3.0"
    assert report.entries[0].configured_value_label == (
        "High Voltage (600 V)"
    )
    assert report.entries[0].configured_value_assessment == (
        "Documented option"
    )


def test_flags_value_outside_purely_numeric_documented_range():
    definition = PowerFlex525ParameterCatalogue().definition(41)
    assert definition is not None
    device = Device(name="Drive")
    device.observed_parameters = [
        ObservedParameterAccess(
            number=41,
            definition=definition,
            configured_value=DeviceParameterValueEvidence(
                lexical_value="700.0",
                source="Dvc.Cfg_AccelTime",
            ),
        )
    ]

    report = build_parameter_setpoint_report(device)

    assert report.entries[0].configured_value_assessment == (
        "Outside documented range"
    )


def test_reports_parameter_qa_advisories():
    catalogue = PowerFlex525ParameterCatalogue()
    definition = catalogue.definition(544)
    assert definition is not None
    device = Device(name="Drive")
    device.observed_parameters = [
        ObservedParameterAccess(
            number=544,
            definition=definition,
            advisories=catalogue.advisories(544),
        )
    ]

    report = build_parameter_setpoint_report(device)
    entry = report.entries[0]

    assert entry.advisory_severity == "High"
    assert entry.advisory_codes == ("PF525-QA-011",)
    assert "omits stop and range checks" in entry.advisory_summaries[0]

    markdown = ParameterReportMarkdownExporter().export(report)

    assert "## Review priorities" in markdown
    assert "### High" in markdown
    assert (
        "- `A544` Reverse Disable: PF525-QA-011 — "
        "AOI write omits stop and range checks."
        in markdown
    )
