from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import convert_controller
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x import CONTROLLER_ATTRIBUTES, CONTROLLER_ELEMENTS


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _capture_controller(xml: str):
    return capture_section(
        ET.fromstring(xml),
        CONTROLLER_ATTRIBUTES,
        CONTROLLER_ELEMENTS,
    )


def test_converts_sample_controller_and_local_chassis():
    element = ET.parse(SAMPLE_L5X).getroot().find("Controller")
    assert element is not None

    controller = convert_controller(
        capture_section(element, CONTROLLER_ATTRIBUTES, CONTROLLER_ELEMENTS)
    )

    assert controller.name == "booster_compressor"
    assert controller.identity.product_name == "1756-L82E"
    assert controller.identity.vendor is not None
    assert controller.identity.vendor.id == 1
    assert controller.identity.revision is not None
    assert (controller.identity.revision.major, controller.identity.revision.minor) == (
        34,
        11,
    )
    chassis = controller.get_chassis("Local Chassis")
    assert chassis is not None
    assert len(chassis.modules) == 7
    assert chassis.get_module(0) is not None
    assert chassis.get_module(0).name == "Local"
    assert chassis.get_module(2) is not None
    assert chassis.get_module(2).name == "DI_Slot2"
    assert chassis.get_module(2).parent is chassis
    assert controller.source_extensions[0].root.name == "Controller"


def test_resolves_remote_module_as_a_child_of_its_parent_module():
    section = _capture_controller(
        """
        <Controller Name="Demo" ProcessorType="Controller" MajorRev="1" MinorRev="2">
          <Modules>
            <Module Name="Local" CatalogNumber="Controller" ParentModule="Local">
              <Ports><Port Address="0" Upstream="false" /></Ports>
            </Module>
            <Module Name="Bridge" CatalogNumber="Bridge" ParentModule="Local">
              <Ports><Port Address="1" Upstream="true" /></Ports>
            </Module>
            <Module Name="RemoteIO" CatalogNumber="Remote" ParentModule="Bridge">
              <Ports><Port Address="192.0.2.10" Upstream="true" /></Ports>
            </Module>
          </Modules>
        </Controller>
        """
    )

    controller = convert_controller(section)

    chassis = controller.get_chassis("Local Chassis")
    assert chassis is not None
    bridge = chassis.get_module(1)
    assert bridge is not None
    assert len(bridge.child_modules) == 1
    remote = bridge.child_modules[0]
    assert remote.name == "RemoteIO"
    assert remote.slot is None
    assert remote.address == "192.0.2.10"
    assert remote.parent is bridge


def test_unknown_module_parent_is_reported_explicitly():
    section = _capture_controller(
        """
        <Controller Name="Demo">
          <Modules>
            <Module Name="Orphan" ParentModule="Missing">
              <Ports><Port Address="1" Upstream="true" /></Ports>
            </Module>
          </Modules>
        </Controller>
        """
    )

    diagnostics = []
    controller = convert_controller(section, diagnostics=diagnostics)

    assert [module.name for module in controller.unplaced_modules] == ["Orphan"]
    assert len(diagnostics) == 1
    assert diagnostics[0].severity is DiagnosticSeverity.ERROR
    assert diagnostics[0].code == "unknown_module_parent"
    assert diagnostics[0].object_name == "Orphan"
