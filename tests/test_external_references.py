import json

from twinforge.analysis import (
    discover_external_references,
    external_reference_inventory_json,
)
from twinforge.model import (
    ConsumedTagConfiguration,
    Controller,
    Identity,
    MessageTagConfiguration,
    Module,
    Program,
    Tag,
)


def test_discovers_only_explicit_external_reference_fields():
    controller = Controller(name="PLC_A", identity=Identity())
    controller.add_unplaced_module(
        Module(
            name="RemoteDrive",
            catalog="ETHERNET-MODULE",
            identity=Identity(),
            address="192.168.1.80",
        )
    )
    controller.add_tag(
        Tag(
            name="ReadRemote",
            data_type="MESSAGE",
            message_configuration=MessageTagConfiguration(
                connection_path="RemoteController, 2, 192.168.1.81",
            ),
        )
    )
    controller.add_tag(
        Tag(
            name="RemoteData",
            data_type="DINT",
            consumed_configuration=ConsumedTagConfiguration(
                producer="PLC_B",
                remote_tag="SharedData",
                rpi=20.0,
            ),
        )
    )
    controller.add_tag(Tag(name="192_168_1_99", data_type="BOOL"))
    program = Program(name="ProgramA")
    program.add_tag(
        Tag(
            name="LegacyData",
            data_type="DINT",
            consumed_configuration=ConsumedTagConfiguration(
                producer="PLC5",
                remote_file=7,
                rpi=50.0,
            ),
        )
    )
    controller.add_program(program)

    inventory = discover_external_references(controller)

    assert len(inventory.references) == 6
    by_field = {(item.source_name, item.source_field): item for item in inventory.references}
    assert by_field[("RemoteDrive", "Address")].kind.value == "ipv4_address"
    assert by_field[("ReadRemote", "ConnectionPath")].kind.value == (
        "symbolic_path"
    )
    assert by_field[("RemoteData", "Producer")].kind.value == (
        "symbolic_controller"
    )
    assert by_field[("RemoteData", "RemoteTag")].value == "SharedData"
    assert by_field[("LegacyData", "RemoteFile")].value == "7"
    assert all(item.source_name != "192_168_1_99" for item in inventory.references)
    document = json.loads(external_reference_inventory_json(inventory))
    assert document["schema_version"] == "1.0"
    assert document["controller_name"] == "PLC_A"


def test_symbolic_module_address_is_not_claimed_as_an_ip_address():
    controller = Controller(name="PLC", identity=Identity())
    controller.add_unplaced_module(
        Module(
            name="RemoteController",
            catalog="1756-EN2T",
            identity=Identity(),
            address="RemoteController",
        )
    )

    reference = discover_external_references(controller).references[0]

    assert reference.kind.value == "symbolic_path"
