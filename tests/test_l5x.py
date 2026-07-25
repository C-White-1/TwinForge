from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.parsers.l5x.capture import CapturedSection, capture_section
from twinforge.parsers.l5x.parser import L5XParser
from twinforge.schema.l5x import (
    CONTROLLER_ATTRIBUTES,
    CONTROLLER_ELEMENTS,
    REDUNDANCY_INFO_ATTRIBUTES,
)
from twinforge.schema.l5x.modules import EKEY_ATTRIBUTES
from twinforge.schema.l5x.spec import AttributeSpec, ElementSpec

SAMPLE_L5X = Path(__file__).parent / "data" / "basic" / "BoosterCompressor_20260128.L5X"


def test_captures_known_child_sections_recursively():
    element = ET.fromstring(
        """
        <Root Name="Example">
            <Known Enabled="true">
                <Nested Value="42">payload</Nested>
            </Known>
        </Root>
        """
    )
    known_attributes = {"Name": AttributeSpec(name="Name", description="")}
    known_elements = {
        "Known": ElementSpec(
            name="Known",
            attributes={
                "Enabled": AttributeSpec(name="Enabled", description=""),
            },
            elements={
                "Nested": ElementSpec(
                    name="Nested",
                    attributes={
                        "Value": AttributeSpec(name="Value", description=""),
                    },
                    content_type="text",
                ),
            },
        ),
    }

    section = capture_section(element, known_attributes, known_elements)

    assert section.attributes == {"Name": "Example"}
    known = section.elements["Known"][0]
    assert isinstance(known, CapturedSection)
    assert known.attributes == {"Enabled": "true"}

    nested = known.elements["Nested"][0]
    assert nested.attributes == {"Value": "42"}
    assert nested.text == "payload"


def test_preserves_unknown_attributes_and_elements_at_each_level():
    element = ET.fromstring(
        """
        <Root KnownAttr="yes" ExtraRootAttr="keep">
            <Known ExtraKnownAttr="keep">
                <UnexpectedChild PreserveMe="yes" />
            </Known>
            <UnexpectedRootChild PreserveMe="yes" />
        </Root>
        """
    )
    known_attributes = {
        "KnownAttr": AttributeSpec(name="KnownAttr", description=""),
    }
    known_elements = {
        "Known": ElementSpec(name="Known"),
    }

    section = capture_section(element, known_attributes, known_elements)

    assert section.extra_attributes == {"ExtraRootAttr": "keep"}
    assert "UnexpectedRootChild" in section.extra_elements
    assert section.extra_elements["UnexpectedRootChild"][0].attrib == {
        "PreserveMe": "yes"
    }

    known = section.elements["Known"][0]
    assert known.extra_attributes == {"ExtraKnownAttr": "keep"}
    assert "UnexpectedChild" in known.extra_elements
    assert known.extra_elements["UnexpectedChild"][0].attrib == {"PreserveMe": "yes"}


def test_controller_security_primary_action_sets_are_nested_sections():
    element = ET.fromstring(
        """
        <Controller Use="Target" Name="Demo">
            <Security Code="0">
                <PrimaryActionSets>
                    <PrimaryActionSet PermissionSet="Guest" IsPermissionSet="true">
                        encoded_permissions
                    </PrimaryActionSet>
                </PrimaryActionSets>
            </Security>
        </Controller>
        """
    )

    section = capture_section(element, {}, CONTROLLER_ELEMENTS)

    security = section.elements["Security"][0]
    action_sets = security.elements["PrimaryActionSets"][0]
    action_set = action_sets.elements["PrimaryActionSet"][0]

    assert security.attributes == {"Code": "0"}
    assert action_set.attributes == {
        "PermissionSet": "Guest",
        "IsPermissionSet": "true",
    }
    assert action_set.text is not None
    assert "encoded_permissions" in action_set.text


def test_sample_controller_modules_are_captured_recursively():
    root = ET.parse(SAMPLE_L5X).getroot()
    controller = root.find("Controller")
    assert controller is not None

    section = capture_section(controller, CONTROLLER_ATTRIBUTES, CONTROLLER_ELEMENTS)

    modules = section.elements["Modules"][0]
    module_sections = modules.elements["Module"]

    assert len(module_sections) == 7

    local = module_sections[0]
    assert local.attributes["Name"] == "Local"
    assert local.attributes["CatalogNumber"] == "1756-L82E"

    ports = local.elements["Ports"][0]
    port_sections = ports.elements["Port"]
    assert len(port_sections) == 2
    assert port_sections[0].attributes == {
        "Id": "1",
        "Address": "0",
        "Type": "ICP",
        "Upstream": "false",
    }
    assert port_sections[0].elements["Bus"][0].attributes == {"Size": "10"}

    digital_input = module_sections[1]
    communications = digital_input.elements["Communications"][0]
    assert communications.attributes == {"CommMethod": "536870913"}

    config_tag = communications.elements["ConfigTag"][0]
    assert config_tag.attributes == {
        "ConfigSize": "24",
        "ExternalAccess": "Read/Write",
    }
    assert "Data" in config_tag.extra_elements

    connections = communications.elements["Connections"][0]
    connection = connections.elements["Connection"][0]
    assert connection.attributes == {
        "Name": "StandardInput",
        "RPI": "20000",
        "Type": "Input",
        "EventID": "0",
        "ProgrammaticallySendEventTrigger": "false",
    }
    assert "InputTag" in connection.elements


def test_report_includes_nested_captured_sections(capsys):
    root = ET.parse(SAMPLE_L5X).getroot()
    controller = root.find("Controller")
    assert controller is not None
    section = capture_section(controller, CONTROLLER_ATTRIBUTES, CONTROLLER_ELEMENTS)

    section.report(max_depth=2)

    output = capsys.readouterr().out
    assert "<Controller>" in output
    assert "  <Modules>" in output
    assert "    <Module>" in output
    assert "Module: 7" in output


def test_l5x_parser_accepts_report_depth(capsys):
    parser = L5XParser()

    parser.parse(SAMPLE_L5X, report_depth=1)

    output = capsys.readouterr().out
    assert "  <Modules>" in output
    assert "    <Module>" not in output


def test_ekey_identity_fields_are_not_applicable_unless_state_is_custom(capsys):
    section = capture_section(
        ET.fromstring('<EKey State="CompatibleModule" />'),
        EKEY_ATTRIBUTES,
        {},
    )

    section.report(mode="debug")

    output = capsys.readouterr().out
    absent = output.split("Optional attributes absent:", 1)[1].split(
        "Documented attributes not applicable:", 1
    )[0]
    not_applicable = output.split("Documented attributes not applicable:", 1)[1]
    assert "Vendor" not in absent
    assert "Vendor" in not_applicable
    assert "ProductType" in not_applicable
    assert "ProductCode" in not_applicable
    assert "Major" in not_applicable
    assert "Minor" in not_applicable


def test_custom_ekey_identity_fields_are_reported_missing(capsys):
    section = capture_section(
        ET.fromstring('<EKey State="Custom" Vendor="37" />'),
        EKEY_ATTRIBUTES,
        {},
    )

    section.report(mode="debug")

    output = capsys.readouterr().out
    absent = output.split("Optional attributes absent:", 1)[1].split(
        "Documented attributes not applicable:", 1
    )[0]
    assert "Vendor: 37" in output
    assert "ProductType" in absent
    assert "ProductCode" in absent
    assert "Major" in absent
    assert "Minor" in absent


def test_vendor_one_is_labeled_without_changing_captured_value(capsys):
    section = capture_section(
        ET.fromstring('<EKey State="Custom" Vendor="1" />'),
        EKEY_ATTRIBUTES,
        {},
    )

    assert section.attributes["Vendor"] == "1"

    section.report()
    output = capsys.readouterr().out
    assert "Vendor: 1 (Allen-Bradley / Rockwell Automation)" in output


def test_summary_suppresses_empty_groups_and_optional_absences(capsys):
    section = capture_section(
        ET.fromstring('<RedundancyInfo Enabled="false" />'),
        REDUNDANCY_INFO_ATTRIBUTES,
        {},
    )

    section.report(mode="summary")

    output = capsys.readouterr().out
    assert "Enabled: false" in output
    assert "Optional attributes absent" not in output
    assert "Extra attributes" not in output
    assert "IOMemoryPadPercentage" not in output


def test_debug_separates_optional_absent_fields(capsys):
    section = capture_section(
        ET.fromstring('<RedundancyInfo Enabled="false" />'),
        REDUNDANCY_INFO_ATTRIBUTES,
        {},
    )

    section.report(mode="debug")

    output = capsys.readouterr().out
    assert "Required attributes missing:" in output
    assert "Optional attributes absent:" in output
    assert "IOMemoryPadPercentage" in output


def test_parser_can_suppress_reporting(capsys):
    plant = L5XParser().parse(SAMPLE_L5X, report_mode=None)

    assert capsys.readouterr().out == ""
    assert plant.name == "booster_compressor"
    assert len(plant.controllers) == 1
    controller = plant.controllers[0]
    assert controller.parent is plant
    assert controller.name == "booster_compressor"
    chassis = controller.get_chassis("Local Chassis")
    assert chassis is not None
    assert len(chassis.modules) == 7
    module = chassis.get_module(2)
    assert module is not None
    assert module.catalog == "1756-IB16"
    assert plant.source_extensions[0].root.name == "RSLogix5000Content"
    assert plant.source_extensions[0].root.attributes["Owner"] == "PLC PRO"


def test_summary_does_not_expand_empty_sections(capsys):
    root = capture_section(
        ET.fromstring("<Root><Empty /></Root>"),
        {},
        {"Empty": ElementSpec(name="Empty")},
    )

    root.report(mode="summary")

    output = capsys.readouterr().out
    assert "Empty: 1" in output
    assert "<Empty>" not in output


def test_summary_prints_compact_truncated_element_text(capsys):
    long_text = "first line\n" + ("x" * 200)
    section = capture_section(
        ET.fromstring(f"<Description><![CDATA[{long_text}]]></Description>"),
        {},
        {},
    )

    section.report(mode="summary")

    output = capsys.readouterr().out
    assert "Text: first line " in output
    assert "\nxxxxxxxx" not in output
    assert "…" in output
    assert long_text not in output


def test_debug_prints_complete_multiline_element_text(capsys):
    section = capture_section(
        ET.fromstring(
            "<Description><![CDATA[Line one\nLine two\nLine three]]></Description>"
        ),
        {},
        {},
    )

    section.report(mode="debug")

    output = capsys.readouterr().out
    assert "Text:\n" in output
    assert "  Line one" in output
    assert "  Line two" in output
    assert "  Line three" in output


def test_report_ignores_whitespace_only_element_text(capsys):
    section = capture_section(ET.fromstring("<Container>  \n  </Container>"), {}, {})

    section.report(mode="debug")

    assert "Text:" not in capsys.readouterr().out
