import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from twinforge.exporters import (
    CAEX_NAMESPACE,
    AutomationMLExporter,
    AutomationMLValidationError,
    validate_automationml_references,
    validate_automationml_xml,
)
from twinforge.parsers import L5XParser
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    GatewayDevice,
    GatewayTagBinding,
    GatewayTagBindingRole,
)


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"
FIXED_TIME = datetime(2026, 7, 25, tzinfo=timezone.utc)


def test_validation_wraps_malformed_caex_schema_as_public_error(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "malformed.xsd"
    schema.write_text("not an XML schema", encoding="utf-8")

    with pytest.raises(AutomationMLValidationError):
        validate_automationml_xml("<CAEXFile/>", schema)


def _find(
    parent: ET.Element,
    path: str,
    namespaces: dict[str, str],
) -> ET.Element:
    """Find a required XML element and narrow its optional return type."""

    element = parent.find(path, namespaces)
    assert element is not None, f"missing XML element: {path}"
    return element


def _export(
    base_library_path: str = (
        "../../reference/AutomationML/"
        "AutomationML2.10BaseLibraries.aml"
    ),
    gateways=(),
):
    controller = L5XParser().parse(
        SAMPLE_L5X, report_mode=None
    ).controllers[0]
    return AutomationMLExporter().export(
        controller,
        project_name="Booster Compressor",
        plcopen_path="../PLCOpenXML/BoosterCompressor_codesys.xml",
        base_library_path=base_library_path,
        last_writing_time=FIXED_TIME,
        gateways=gateways,
    )


def _gateway(controller) -> GatewayDevice:
    gateway = GatewayDevice(
        name="FieldbusGateway",
        manufacturer="Example Vendor",
        model="Protocol Gateway",
    )
    gateway.add_communication_interface(
        CommunicationInterface(
            name="EtherNet/IP",
            protocol="EtherNet/IP",
            role=CommunicationRole.ADAPTER,
        )
    )
    tag = controller.tags["PT102_PV"]
    gateway.add_tag_binding(
        GatewayTagBinding(
            interface_name="EtherNet/IP",
            endpoint_reference="Gateway:I1.Data[72]",
            tag=tag,
            tag_path=tag.name,
            role=GatewayTagBindingRole.TARGET,
            evidence="configuration plus generated mapping",
        )
    )
    return gateway


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
    assert _find(
        root,
        ".//c:InternalElement[@Name='AI_Slot4']/"
        "c:Attribute[@Name='Slot']/c:Value",
        ns,
    ).text == "4"
    assert _find(
        root,
        ".//c:InternalElement[@Name='Local']/"
        "c:Attribute[@Name='AssetType']/c:Value",
        ns,
    ).text == "Controller"
    assert _find(
        root,
        ".//c:InternalElement[@Name='AI_Slot4']/"
        "c:Attribute[@Name='AssetType']/c:Value",
        ns,
    ).text == "IOModule"


def test_exports_gateway_tag_bindings_as_linked_communication_interfaces():
    controller = L5XParser().parse(
        SAMPLE_L5X, report_mode=None
    ).controllers[0]
    result = AutomationMLExporter().export(
        controller,
        project_name="Booster Compressor",
        base_library_path=(
            "../../tests/data/automationml_base_libraries.aml"
        ),
        last_writing_time=FIXED_TIME,
        gateways=(_gateway(controller),),
    )
    root = ET.fromstring(result.xml)
    ns = {"c": CAEX_NAMESPACE}
    gateway = _find(
        root,
        ".//c:InternalElement[@Name='FieldbusGateway']",
        ns,
    )
    assert _find(
        gateway,
        "c:Attribute[@Name='AssetType']/c:Value",
        ns,
    ).text == "CommunicationGateway"
    gateway_interface = _find(
        gateway,
        "c:ExternalInterface",
        ns,
    )
    assert gateway_interface.attrib["RefBaseClassPath"].endswith(
        "/CommunicationPointInterface"
    )
    assert _find(
        gateway_interface,
        "c:Attribute[@Name='Direction']/c:Value",
        ns,
    ).text == "Out"
    plc_interface = _find(
        root,
        ".//c:InternalElement[@Name='booster_compressor']/"
        "c:ExternalInterface[@Name='PT102_PV']",
        ns,
    )
    assert _find(
        plc_interface,
        "c:Attribute[@Name='Direction']/c:Value",
        ns,
    ).text == "In"
    link = _find(
        root,
        ".//c:InternalLink[@Name='PT102_PV_to_Gateway:I1.Data[72]']",
        ns,
    )
    assert link.attrib["RefPartnerSideA"] == plc_interface.attrib["ID"]
    assert link.attrib["RefPartnerSideB"] == gateway_interface.attrib["ID"]
    validate_automationml_references(
        result.xml,
        Path(__file__).parents[1]
        / "examples/AutomationML/gateway-bindings.aml",
    )


def test_links_process_signals_to_module_channels_with_units():
    root = ET.fromstring(_export().xml)
    ns = {"c": CAEX_NAMESPACE}
    signal = root.find(".//c:InternalElement[@Name='PT102_PV']", ns)
    assert signal is not None
    assert _find(
        signal,
        "c:Attribute[@Name='EngineeringUnit']/c:Value", ns
    ).text == "barg"
    assert _find(
        signal,
        "c:Attribute[@Name='LowerRangeValue']/c:Value", ns
    ).text == "0"
    assert _find(
        signal,
        "c:Attribute[@Name='UpperRangeValue']/c:Value", ns
    ).text == "150"
    signal_interface = signal.find("c:ExternalInterface[@Name='Signal']", ns)
    assert signal_interface is not None
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
    assert _find(
        digital,
        "c:Attribute[@Name='AssetType']/c:Value", ns
    ).text == "DigitalSignal"
    digital_interface = root.find(
        ".//c:InternalElement[@Name='DI_Slot2']/"
        "c:ExternalInterface[@Name='i.data.0']",
        ns,
    )
    assert digital_interface is not None
    digital_module = _find(
        root,
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
    assert _find(
        digital_module,
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
    controller = _find(
        root,
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
    pt102 = _find(
        root,
        ".//c:InternalElement[@Name='PT102_PV']",
        ns,
    )
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
    analog_module = _find(
        root,
        ".//c:InternalElement[@Name='AI_Slot4']", ns
    )
    assert _find(
        analog_module,
        "c:Attribute[@Name='NominalChannelCount']/c:Value", ns
    ).text == "8"
    assert _find(
        analog_module,
        "c:Attribute[@Name='ConfiguredChannelCount']/c:Value", ns
    ).text == "4"
    assert _find(
        analog_module,
        "c:Attribute[@Name='UnavailableByConfigurationCount']/c:Value",
        ns,
    ).text == "4"
    assert analog_module.find(
        "c:ExternalInterface[@Name='i.ch4data']", ns
    ) is None
    analog_output = _find(
        root,
        ".//c:InternalElement[@Name='AO_Slot5']", ns
    )
    assert analog_output.find(
        "c:ExternalInterface[@Name='o.ch0data']", ns
    ) is not None
    assert analog_output.find(
        "c:ExternalInterface[@Name='i.ch0data']", ns
    ) is None
    assert _find(
        analog_output,
        "c:Attribute[@Name='o.ch0data.EngineeringUnit']/c:Value",
        ns,
    ).text == "%"
    assert _find(
        analog_output,
        "c:Attribute[@Name='o.ch0data.AssignmentStatus']/c:Value",
        ns,
    ).text == "Assigned"
    assert analog_output.find(
        "c:Attribute[@Name='o.ch0data.LogicReferences']/c:Value",
        ns,
    ) is not None
    assert _find(
        analog_output,
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
    # Use a tracked, minimal fixture here so the semantic validator is tested
    # in clean clones without redistributing the official reference library.
    result = _export(
        "../../tests/data/automationml_base_libraries.aml"
    )
    destination = (
        Path(__file__).parents[1]
        / "examples/AutomationML/BoosterCompressor.aml"
    )
    validate_automationml_references(result.xml, destination)
