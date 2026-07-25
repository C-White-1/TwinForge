from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.converters.l5x import convert_module
from twinforge.model import (
    EngineeringUnitConfidence,
    EngineeringUnitSource,
    IODirection,
    IOSignalType,
    KeyingMode,
)
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x.modules import MODULE_ATTRIBUTES, MODULE_ELEMENTS


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _capture_module(xml: str):
    return capture_section(
        ET.fromstring(xml),
        MODULE_ATTRIBUTES,
        MODULE_ELEMENTS,
    )


def test_converts_sample_module_identity_slot_flags_and_ekey():
    root = ET.parse(SAMPLE_L5X).getroot()
    element = root.find("./Controller/Modules/Module[@Name='DI_Slot2']")
    assert element is not None

    module = convert_module(
        capture_section(element, MODULE_ATTRIBUTES, MODULE_ELEMENTS)
    )

    assert module.name == "DI_Slot2"
    assert module.slot == 2
    assert module.catalog == "1756-IB16"
    assert module.identity.vendor is not None
    assert module.identity.vendor.id == 1
    assert module.identity.vendor.name == "Allen-Bradley / Rockwell Automation"
    assert module.identity.product_type == 7
    assert module.identity.product_code == 11
    assert module.identity.revision is not None
    assert (module.identity.revision.major, module.identity.revision.minor) == (3, 1)
    assert module.inhibited is False
    assert module.major_fault_on_connection_loss is False
    assert len(module.connections) == 1
    assert module.connections[0].name == "StandardInput"
    assert module.connections[0].connection_type == "Input"
    assert module.connections[0].parent is module
    assert module.connections[0].source_extensions[0].root.name == "Connection"
    assert module.electronic_key is not None
    assert module.electronic_key.mode is KeyingMode.COMPATIBLE_MODULE
    assert module.electronic_key.identity is None
    assert module.source_extensions[0].root.attributes["Vendor"] == "1"
    assert module.identity.source_extensions[0].root.name == "Module"


def test_converts_module_channel_engineering_units():
    root = ET.parse(SAMPLE_L5X).getroot()
    element = root.find("./Controller/Modules/Module[@Name='AI_Slot4']")
    assert element is not None

    module = convert_module(
        capture_section(element, MODULE_ATTRIBUTES, MODULE_ELEMENTS)
    )

    channel = module.engineering_units["i.ch2data"]
    assert channel.symbol == "barg"
    assert channel.source is EngineeringUnitSource.MODULE_CHANNEL
    assert channel.confidence is EngineeringUnitConfidence.EXPLICIT
    assert channel.source_operand == "Local:4:I.CH2DATA"
    engineering_range = module.engineering_ranges["i.ch2data"]
    assert engineering_range.lower == 0.0
    assert engineering_range.upper == 150.0
    assert engineering_range.source_operand == "Local:4:C.Ch2Config"
    assert module.capability is not None
    assert module.capability.signal_type is IOSignalType.ANALOG
    assert module.capability.direction is IODirection.INPUT
    assert module.capability.nominal_channel_count == 8
    assert module.capability.configured_channel_count == 4
    assert module.capability.unavailable_by_configuration_count == 4


def test_decodes_digital_module_nominal_capacity_from_catalog_convention():
    root = ET.parse(SAMPLE_L5X).getroot()
    element = root.find("./Controller/Modules/Module[@Name='DI_Slot2']")
    assert element is not None

    module = convert_module(
        capture_section(element, MODULE_ATTRIBUTES, MODULE_ELEMENTS)
    )

    assert module.capability is not None
    assert module.capability.signal_type is IOSignalType.DIGITAL
    assert module.capability.direction is IODirection.INPUT
    assert module.capability.nominal_channel_count == 16
    assert module.capability.configured_channel_count == 16


def test_converts_custom_ekey_as_a_separate_identity():
    section = _capture_module(
        """
        <Module Name="ThirdParty" CatalogNumber="XYZ" Vendor="1"
                ProductType="7" ProductCode="11" Major="3" Minor="1">
            <EKey State="Custom" Vendor="37" ProductType="12"
                  ProductCode="42" Major="1" Minor="5" />
            <Ports><Port Id="1" Address="4" Upstream="true" /></Ports>
        </Module>
        """
    )

    module = convert_module(section)

    assert module.identity.vendor is not None
    assert module.identity.vendor.id == 1
    assert module.electronic_key is not None
    assert module.electronic_key.mode is KeyingMode.CUSTOM
    assert module.electronic_key.identity is not None
    assert module.electronic_key.identity.vendor is not None
    assert module.electronic_key.identity.vendor.id == 37
    assert module.electronic_key.identity.vendor.name is None
    assert module.electronic_key.identity.product_type == 12
    assert module.electronic_key.identity.revision is not None
    assert module.electronic_key.identity.revision.minor == 5


def test_unknown_ekey_state_and_source_data_are_preserved():
    section = _capture_module(
        """
        <Module Name="Future" FutureAttribute="keep">
            <EKey State="FutureMode" FutureKeyAttribute="keep" />
        </Module>
        """
    )

    module = convert_module(section, slot=8)

    assert module.electronic_key is not None
    assert module.electronic_key.mode is None
    assert module.electronic_key.unknown_mode == "FutureMode"
    assert module.source_extensions[0].root.attributes["FutureAttribute"] == "keep"
    assert (
        module.electronic_key.source_extensions[0]
        .root.attributes["FutureKeyAttribute"]
        == "keep"
    )


def test_non_numeric_address_is_preserved_without_inventing_a_slot():
    section = _capture_module(
        """
        <Module Name="Remote" CatalogNumber="Adapter">
            <Ports><Port Id="1" Address="192.0.2.10" Upstream="true" /></Ports>
        </Module>
        """
    )

    module = convert_module(section)

    assert module.slot is None
    assert module.address == "192.0.2.10"
    assert convert_module(section, slot=3).slot == 3
