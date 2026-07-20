import xml.etree.ElementTree as ET

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import convert_module
from twinforge.parsers.l5x.capture import capture_section
from twinforge.parsers import L5XParser
from twinforge.schema.l5x.modules import MODULE_ATTRIBUTES, MODULE_ELEMENTS


def _module(xml: str):
    return capture_section(
        ET.fromstring(xml),
        MODULE_ATTRIBUTES,
        MODULE_ELEMENTS,
    )


def test_reports_malformed_values_without_losing_source_data():
    section = _module(
        """
        <Module Name="Malformed" Vendor="not-an-int" ProductType="7"
                Inhibited="perhaps" Major="3">
          <Ports><Port Address="2" Upstream="true" /></Ports>
        </Module>
        """
    )
    diagnostics = []

    module = convert_module(section, diagnostics=diagnostics)

    assert module.identity.vendor is None
    assert module.inhibited is None
    assert module.source_extensions[0].root.attributes["Vendor"] == "not-an-int"
    assert {item.code for item in diagnostics} == {
        "invalid_integer",
        "invalid_boolean",
        "incomplete_revision",
    }
    assert all(item.severity is DiagnosticSeverity.WARNING for item in diagnostics)


def test_reports_unknown_vendor_and_incomplete_custom_key():
    section = _module(
        """
        <Module Name="ThirdParty" Vendor="37">
          <EKey State="Custom" Vendor="37" />
          <Ports><Port Address="3" Upstream="true" /></Ports>
        </Module>
        """
    )
    diagnostics = []

    convert_module(section, diagnostics=diagnostics)

    codes = [item.code for item in diagnostics]
    assert codes.count("unknown_vendor") == 2
    assert "incomplete_custom_ekey" in codes
    assert next(item for item in diagnostics if item.code == "unknown_vendor").severity \
        is DiagnosticSeverity.INFO


def test_reports_unknown_keying_mode():
    section = _module(
        """
        <Module Name="Future">
          <EKey State="FutureMode" />
          <Ports><Port Address="4" Upstream="true" /></Ports>
        </Module>
        """
    )
    diagnostics = []

    module = convert_module(section, diagnostics=diagnostics)

    assert module.electronic_key is not None
    assert module.electronic_key.unknown_mode == "FutureMode"
    assert diagnostics[0].code == "unknown_keying_mode"
    assert diagnostics[0].raw_value == "FutureMode"


def test_parser_exposes_and_resets_conversion_diagnostics(tmp_path):
    source = tmp_path / "malformed.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="Demo">
          <Controller Name="Demo">
            <Modules>
              <Module Name="Local" ParentModule="Local" Vendor="invalid">
                <Ports><Port Address="0" Upstream="false" /></Ports>
              </Module>
            </Modules>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    plant = parser.parse(source, report_mode=None)

    assert plant.name == "Demo"
    assert parser.diagnostics[0].code == "invalid_integer"
    assert parser.diagnostics[0].field == "Vendor"

    parser.parse(source, report_mode=None)
    assert len(parser.diagnostics) == 1
