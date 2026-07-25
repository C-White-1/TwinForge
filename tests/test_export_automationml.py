import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from twinforge.exporters import (
    CAEX_NAMESPACE,
    AutomationMLExporter,
    validate_automationml_references,
    validate_automationml_xml,
)
from twinforge.parsers import L5XParser


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"
FIXED_TIME = datetime(2026, 7, 25, tzinfo=timezone.utc)


def _export():
    controller = L5XParser().parse(
        SAMPLE_L5X, report_mode=None
    ).controllers[0]
    return AutomationMLExporter().export(
        controller,
        project_name="Booster Compressor",
        plcopen_path="../PLCOpenXML/BoosterCompressor_codesys.xml",
        base_library_path=(
            "../../reference/AutomationML/"
            "AutomationML2.10BaseLibraries.aml"
        ),
        last_writing_time=FIXED_TIME,
    )


def test_exports_native_editor_compatible_caex_hierarchy():
    root = ET.fromstring(_export().xml)
    ns = {"c": CAEX_NAMESPACE}

    assert root.attrib["SchemaVersion"] == "3.0"
    assert root.findtext("c:SuperiorStandardVersion", namespaces=ns) == (
        "AutomationML 2.1"
    )
    assert root.find(
        "c:InstanceHierarchy/c:InternalElement[@Name='Booster Compressor']/"
        "c:InternalElement[@Name='booster_compressor']",
        ns,
    ) is not None
    assert root.find(
        ".//c:InternalElement[@Name='AI_Slot4']/"
        "c:Attribute[@Name='Slot']/c:Value",
        ns,
    ).text == "4"
    assert root.find(
        ".//c:InternalElement[@Name='Local']/"
        "c:Attribute[@Name='AssetType']/c:Value",
        ns,
    ).text == "Controller"
    assert root.find(
        ".//c:InternalElement[@Name='AI_Slot4']/"
        "c:Attribute[@Name='AssetType']/c:Value",
        ns,
    ).text == "IOModule"


def test_links_process_signals_to_module_channels_with_units():
    root = ET.fromstring(_export().xml)
    ns = {"c": CAEX_NAMESPACE}
    signal = root.find(".//c:InternalElement[@Name='PT102_PV']", ns)
    assert signal is not None
    assert signal.find(
        "c:Attribute[@Name='EngineeringUnit']/c:Value", ns
    ).text == "barg"
    assert signal.find(
        "c:Attribute[@Name='LowerRangeValue']/c:Value", ns
    ).text == "0"
    assert signal.find(
        "c:Attribute[@Name='UpperRangeValue']/c:Value", ns
    ).text == "150"
    signal_interface = signal.find("c:ExternalInterface[@Name='Signal']", ns)
    module_interface = root.find(
        ".//c:InternalElement[@Name='AI_Slot4']/"
        "c:ExternalInterface[@Name='i.ch2data']",
        ns,
    )
    assert module_interface is not None
    assert root.find(
        ".//c:InternalElement[@Name='AI_Slot4']/"
        "c:ExternalInterface[@Name='o.ch1data']",
        ns,
    ) is None
    link = root.find(".//c:InternalLink[@Name='PT102_PV_to_IO']", ns)
    assert link is not None
    assert link.attrib["RefPartnerSideA"] == signal_interface.attrib["ID"]
    assert link.attrib["RefPartnerSideB"] == module_interface.attrib["ID"]

    digital = root.find(".//c:InternalElement[@Name='XV101_Open']", ns)
    assert digital is not None
    assert digital.find(
        "c:Attribute[@Name='AssetType']/c:Value", ns
    ).text == "DigitalSignal"
    digital_interface = root.find(
        ".//c:InternalElement[@Name='DI_Slot2']/"
        "c:ExternalInterface[@Name='i.data.0']",
        ns,
    )
    assert digital_interface is not None
    digital_module = root.find(
        ".//c:InternalElement[@Name='DI_Slot2']", ns
    )
    interface_names = [
        interface.attrib["Name"]
        for interface in digital_module.findall("c:ExternalInterface", ns)
    ]
    assert interface_names.index("i.data.2") < interface_names.index(
        "i.data.11"
    )
    digital_attributes = {
        attribute.attrib["Name"]: attribute.findtext(
            "c:Value", namespaces=ns
        )
        for attribute in digital_module.findall("c:Attribute", ns)
    }
    assert digital_attributes["i.data.0.SignalType"] == "Digital"
    assert (
        digital_attributes["i.data.0.SourceOperand"]
        == "Local:2:I.Data.0"
    )
    assert digital_attributes["i.data.0.AssignedTags"] == "XV101_Open"
    assert digital_attributes["i.data.8.AssignmentStatus"] == "Spare"
    assert digital_attributes["i.data.10.AssignmentStatus"] == "Spare"
    assert digital_attributes["i.data.0.AssignmentStatus"] == "Assigned"
    assert digital_module.find(
        "c:Attribute[@Name='NominalChannelCount']/c:Value", ns
    ).text == "16"
    assert root.find(
        ".//c:InternalLink[@Name='XV101_Open_to_IO']", ns
    ) is not None


def test_export_is_deterministic():
    assert _export().xml == _export().xml


def test_exports_semantic_libraries_roles_and_plcopen_interface():
    root = ET.fromstring(_export().xml)
    ns = {"c": CAEX_NAMESPACE}

    reference = root.find(
        "c:ExternalReference[@Alias='AutomationMLBaseLibraries']", ns
    )
    assert reference is not None
    assert reference.attrib["Path"].endswith(
        "AutomationML2.10BaseLibraries.aml"
    )
    analog_class = root.find(
        "c:InterfaceClassLib[@Name='TwinForgeInterfaceClassLib']/"
        "c:InterfaceClass[@Name='AnalogSignalInterface']",
        ns,
    )
    assert analog_class is not None
    assert analog_class.attrib["RefBaseClassPath"].endswith(
        "@AutomationMLInterfaceClassLib/AutomationMLBaseInterface/"
        "Communication/SignalInterface"
    )
    controller = root.find(
        ".//c:InternalElement[@Name='booster_compressor']", ns
    )
    assert controller.find(
        "c:RoleRequirements"
        "[@RefBaseRoleClassPath='TwinForgeRoleClassLib/Controller']",
        ns,
    ) is not None
    plcopen = controller.find(
        "c:ExternalInterface[@Name='PLCopenXML']", ns
    )
    assert plcopen is not None
    assert plcopen.attrib["RefBaseClassPath"].endswith(
        "/ExternalDataConnector/PLCopenXMLInterface"
    )
    assert plcopen.findtext(
        "c:Attribute[@Name='refURI']/c:Value", namespaces=ns
    ) == "../PLCOpenXML/BoosterCompressor_codesys.xml"
    pt102 = root.find(".//c:InternalElement[@Name='PT102_PV']", ns)
    assert pt102.find(
        "c:RoleRequirements"
        "[@RefBaseRoleClassPath='TwinForgeRoleClassLib/"
        "AnalogProcessSignal']",
        ns,
    ) is not None
    assert pt102.find(
        "c:ExternalInterface[@Name='Signal']"
        "[@RefBaseClassPath='TwinForgeInterfaceClassLib/"
        "AnalogSignalInterface']",
        ns,
    ) is not None


def test_exports_vendor_neutral_and_catalog_system_unit_classes():
    root = ET.fromstring(_export().xml)
    ns = {"c": CAEX_NAMESPACE}

    assert root.find(
        "c:SystemUnitClassLib[@Name='TwinForgeSystemUnitClassLib']/"
        "c:SystemUnitClass[@Name='AnalogInputModule']"
        "[@RefBaseClassPath='TwinForgeSystemUnitClassLib/IOModule']",
        ns,
    ) is not None
    analog_module = root.find(
        ".//c:InternalElement[@Name='AI_Slot4']", ns
    )
    assert analog_module.find(
        "c:Attribute[@Name='NominalChannelCount']/c:Value", ns
    ).text == "8"
    assert analog_module.find(
        "c:Attribute[@Name='ConfiguredChannelCount']/c:Value", ns
    ).text == "4"
    assert analog_module.find(
        "c:Attribute[@Name='UnavailableByConfigurationCount']/c:Value",
        ns,
    ).text == "4"
    assert analog_module.find(
        "c:ExternalInterface[@Name='i.ch4data']", ns
    ) is None
    analog_output = root.find(
        ".//c:InternalElement[@Name='AO_Slot5']", ns
    )
    assert analog_output.find(
        "c:ExternalInterface[@Name='o.ch0data']", ns
    ) is not None
    assert analog_output.find(
        "c:ExternalInterface[@Name='i.ch0data']", ns
    ) is None
    assert analog_output.find(
        "c:Attribute[@Name='o.ch0data.EngineeringUnit']/c:Value",
        ns,
    ).text == "%"
    assert analog_output.find(
        "c:Attribute[@Name='o.ch0data.AssignmentStatus']/c:Value",
        ns,
    ).text == "Assigned"
    assert analog_output.find(
        "c:Attribute[@Name='o.ch0data.LogicReferences']/c:Value",
        ns,
    ) is not None
    assert analog_output.find(
        "c:Attribute[@Name='o.ch2data.AssignmentStatus']/c:Value",
        ns,
    ).text == "Spare"
    assert root.find(
        "c:SystemUnitClassLib[@Name='RockwellSystemUnitClassLib']/"
        "c:SystemUnitClass[@Name='1756-IF8']"
        "[@RefBaseClassPath='TwinForgeSystemUnitClassLib/"
        "AnalogInputModule']",
        ns,
    ) is not None
    assert root.find(
        "c:SystemUnitClassLib[@Name='RockwellSystemUnitClassLib']/"
        "c:SystemUnitClass[@Name='1756-OB16E']"
        "[@RefBaseClassPath='TwinForgeSystemUnitClassLib/"
        "DigitalOutputModule']",
        ns,
    ) is not None
    assert root.find(
        ".//c:InternalElement[@Name='AI_Slot4']"
        "[@RefBaseSystemUnitPath='RockwellSystemUnitClassLib/1756-IF8']",
        ns,
    ) is not None
    assert root.find(
        ".//c:InternalElement[@Name='XV101_Open']"
        "[@RefBaseSystemUnitPath='TwinForgeSystemUnitClassLib/"
        "DigitalInputSignal']",
        ns,
    ) is not None
    assert root.find(
        ".//c:InternalElement[@Name='PT102_PV']"
        "[@RefBaseSystemUnitPath='TwinForgeSystemUnitClassLib/"
        "AnalogInputSignal']",
        ns,
    ) is not None


def test_generated_document_validates_against_local_caex_schema():
    schema = (
        Path(__file__).parents[1]
        / "reference/AutomationML/CAEX_ClassModel_V.3.0.xsd"
    )
    if schema.exists():
        validate_automationml_xml(_export().xml, schema)


def test_generated_document_resolves_all_local_and_external_references():
    result = _export()
    destination = (
        Path(__file__).parents[1]
        / "examples/AutomationML/BoosterCompressor.aml"
    )
    validate_automationml_references(result.xml, destination)
