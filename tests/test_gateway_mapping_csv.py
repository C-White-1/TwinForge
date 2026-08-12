from pathlib import Path

from twinforge.assembly import apply_gateway_mapping_document
from twinforge.model import CommunicationInterface, GatewayDevice
from twinforge.parsers import GatewayMappingCSVParser


def test_preserves_and_applies_explicit_gateway_mapping_rows(tmp_path: Path):
    source = tmp_path / "mappings.csv"
    source.write_text(
        "mapping_id,source_interface,source_reference,target_interface,target_reference,evidence,engineering_unit\n"
        "M1,PROFIBUS DP,station 3/input byte 0,EtherNet/IP,input assembly/offset 12,configuration report row 17,bar\n"
        "M2,PROFIBUS DP,station 4/input byte 0,Modbus TCP,holding register 40001,manual schedule row 9,degC\n",
        encoding="utf-8",
    )
    document = GatewayMappingCSVParser().parse(source)
    gateway = GatewayDevice(name="Gateway")
    gateway.add_communication_interface(
        CommunicationInterface(name="PROFIBUS DP", protocol="PROFIBUS DP")
    )
    gateway.add_communication_interface(
        CommunicationInterface(name="EtherNet/IP", protocol="EtherNet/IP")
    )

    result = apply_gateway_mapping_document(gateway, document)

    assert len(document.records) == 2
    assert document.records[0].metadata == {"engineering_unit": "bar"}
    assert len(result.applied) == 1
    assert result.applied[0].source_reference == "station 3/input byte 0"
    assert result.applied[0].metadata["engineering_unit"] == "bar"
    assert result.unresolved_rows == (3,)
    assert result.diagnostics[0].code == "gateway_mapping_interface_unresolved"
    assert len(gateway.protocol_mappings) == 1
    assert gateway.metadata["protocol_mapping_status"] == "partially_evidenced"


def test_incomplete_rows_are_retained_but_not_promoted(tmp_path: Path):
    source = tmp_path / "incomplete.csv"
    source.write_text(
        "mapping_id,source_interface,target_interface,evidence,future\n"
        "M1,PROFIBUS DP,,manual row 1,keep\n"
        "M2,PROFIBUS DP,EtherNet/IP,,retain\n",
        encoding="utf-8",
    )

    document = GatewayMappingCSVParser().parse(source)

    assert len(document.records) == 2
    assert document.records[0].values[-1] == ("future", "keep")
    assert document.records[1].values[-1] == ("future", "retain")
    assert not document.records[0].promotable
    assert not document.records[1].promotable
    assert [item.code for item in document.diagnostics] == [
        "gateway_mapping_required_value_missing",
        "gateway_mapping_required_value_missing",
    ]
