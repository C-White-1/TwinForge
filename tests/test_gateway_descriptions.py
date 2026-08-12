from pathlib import Path

from twinforge.assembly import assemble_gateway_descriptions
from twinforge.model import CommunicationRole
from twinforge.parsers import EDSParser, GSDParser


def _descriptions(tmp_path: Path, *, gsd_model: str = "PLX51-PBM"):
    eds_path = tmp_path / "gateway.eds"
    eds_path.write_text(
        """
[Device]
VendCode = 309;
VendName = "ProSoft Technology";
ProdType = 12;
ProdTypeStr = "Communications Adapter";
ProdCode = 0x146C;
MajRev = 1;
MinRev = 1;
ProdName = "PLX51-PBM";
[Assembly]
Assem1 = "Input",,,0,,,4000,Param2;
Assem2 = "Output",,,0,,,3968,Param2;
[Connection Manager]
Connection1 = 0x04010002,0x44640405,Param1,496,Assem2,Param1,500,Assem1,,,0,,"I/O","","20 04 24 66 2C 85 2C 84";
""",
        encoding="utf-8",
    )
    gsd_path = tmp_path / "gateway.gsd"
    gsd_path.write_text(
        f"""
#Profibus_DP
Vendor_Name = "ProSoft Technology, Inc."
Model_Name = "{gsd_model}"
Ident_Number = 0x10FE
Station_Type = 0
Max_Module = 40
Max_Input_Len = 244
Max_Output_Len = 244
Max_Data_Len = 488
Module = "Input: 1 Byte" 0x90
1
EndModule
""",
        encoding="latin-1",
    )
    return EDSParser().parse(eds_path), GSDParser().parse(gsd_path)


def test_assembles_descriptions_as_separate_unmapped_protocol_endpoints(
    tmp_path: Path,
):
    eds, gsd = _descriptions(tmp_path)

    result = assemble_gateway_descriptions(eds, gsd)

    gateway = result.gateway
    assert gateway.name == "PLX51-PBM"
    assert gateway.manufacturer == "ProSoft Technology"
    assert gateway.identity is not eds.identity
    assert gateway.metadata["protocol_mapping_status"] == "not_evidenced"
    assert gateway.protocol_mappings == []
    assert [item.protocol for item in gateway.communication_interfaces] == [
        "EtherNet/IP",
        "PROFIBUS DP",
    ]
    ethernet_ip, profibus = gateway.communication_interfaces
    assert ethernet_ip.role is CommunicationRole.ADAPTER
    assert len(ethernet_ip.connections) == 1
    connection = ethernet_ip.connections[0]
    assert connection.input_size_bytes is None
    assert connection.output_size_bytes is None
    assert connection.metadata["configured_size_status"] == "not_evidenced"
    assert connection.metadata["originator_to_target"] == {
        "assembly_reference": "Assem2",
        "declared_size": 496,
        "parameter_reference": "Param1",
    }
    assert profibus.role is CommunicationRole.SLAVE
    assert profibus.metadata["ident_number"] == 0x10FE
    assert profibus.metadata["limits"] == {
        "max_modules": 40,
        "max_input_length": 244,
        "max_output_length": 244,
        "max_data_length": 488,
    }
    assert result.diagnostics == ()


def test_description_model_mismatch_is_reported_without_discarding_sources(
    tmp_path: Path,
):
    eds, gsd = _descriptions(tmp_path, gsd_model="Different Gateway")

    result = assemble_gateway_descriptions(eds, gsd)

    assert result.gateway.name == "PLX51-PBM"
    assert result.diagnostics[0].code == "gateway_description_model_mismatch"
    assert result.gateway.metadata["description_sources"] == {
        "EDS": str(eds.source_path),
        "GSD": str(gsd.source_path),
    }
