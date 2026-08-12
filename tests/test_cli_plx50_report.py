import base64
from io import StringIO
from pathlib import Path

from twinforge.cli import main


def _sources(tmp_path: Path, *, primary: str = "EtherNetIP") -> tuple[Path, ...]:
    eds = tmp_path / "gateway.eds"
    eds.write_text(
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
""",
        encoding="utf-8",
    )
    gsd = tmp_path / "gateway.gsd"
    gsd.write_text(
        """
#Profibus_DP
Vendor_Name = "ProSoft Technology"
Model_Name = "PLX51-PBM"
Ident_Number = 0x10FE
Station_Type = 0
Max_Module = 40
Module = "Input: 4 Bytes" 0x93
EndModule
""",
        encoding="latin-1",
    )
    config = tmp_path / "gateway.psj"
    native_xml = f"""
<ProjectConfig xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Devices><GenericDevice xsi:type="PSPBDevicePLX51PBM"
   DeviceName="Gateway" ConnectionPath="192.0.2.50">
    <Config InstanceName="Gateway" IPAddress="192.0.2.50"
     Mode="StandaloneMaster" PrimaryInterface="{primary}">
      <DeviceConfig><PSPBConfigDevice InstanceName="Device03"
       StationAddress="3" Ident="4350"><Slots>
        <PSPBConfigSlot SlotID="1" ModuleID="3"><DataPoints>
          <PSPBConfigSlotDataPoint DataPointType="Input" DataFormat="REAL"
           ByteLength="4" LocalOffset="0" Description="Input4Bytes"
           ModbusRegisterType="HR" InterfaceConnectionOffset="301" />
        </DataPoints></PSPBConfigSlot>
      </Slots></PSPBConfigDevice></DeviceConfig>
    </Config>
  </GenericDevice></Devices>
</ProjectConfig>
"""
    config.write_text(
        base64.b64encode(
            bytes(value ^ 0x5A for value in native_xml.encode("utf-8"))
        ).decode("ascii"),
        encoding="ascii",
    )
    mapping = tmp_path / "mapping.L5X"
    mapping.write_text(
        """
<RSLogix5000Content TargetType="Routine" TargetName="GatewayMap">
  <Controller Use="Context" Name="Controller">
    <DataTypes>
      <DataType Name="DeviceInput"><Members>
        <Member Name="Input4Bytes" DataType="REAL" Dimension="0" />
      </Members></DataType>
      <DataType Name="Device"><Members>
        <Member Name="Input" DataType="DeviceInput" Dimension="0" />
      </Members></DataType>
    </DataTypes>
    <Tags><Tag Name="Gateway_Device03" TagType="Base" DataType="Device" /></Tags>
    <Programs><Program Use="Context" ProgramName="MainProgram">
      <Routines><Routine Use="Target" Name="GatewayMap" Type="RLL">
        <RLLContent><Rung Number="0" Type="N"><Text>
          MOV(3,Gateway_Device03.Output.Control.StationNumber)
          CPS(Gateway:I1.Data[72],Gateway_Device03.Input,1);
        </Text></Rung></RLLContent>
      </Routine></Routines>
    </Program></Programs>
  </Controller>
</RSLogix5000Content>
""",
        encoding="utf-8",
    )
    return eds, gsd, config, mapping


def test_gateway_report_correlates_offline_sources(tmp_path: Path) -> None:
    eds, gsd, config, mapping = _sources(tmp_path)
    destination = tmp_path / "reports"
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "gateway",
            "report",
            "--eds",
            str(eds),
            "--gsd",
            str(gsd),
            "--config",
            str(config),
            "--mapping",
            str(mapping),
            "--output",
            str(destination),
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert "Correlated points: 1" in output.getvalue()
    report = (destination / "plx50_logix_mapping.md").read_text(
        encoding="utf-8"
    )
    assert "Gateway_Device03.Input.Input4Bytes" in report
    assert "Gateway:I1.Data[72]" in report


def test_gateway_report_rejects_non_logix_primary_without_writing(
    tmp_path: Path,
) -> None:
    eds, gsd, config, mapping = _sources(
        tmp_path,
        primary="ModbusTCPSlave",
    )
    destination = tmp_path / "reports"
    errors = StringIO()

    result = main(
        (
            "gateway",
            "report",
            "--eds",
            str(eds),
            "--gsd",
            str(gsd),
            "--config",
            str(config),
            "--mapping",
            str(mapping),
            "--output",
            str(destination),
        ),
        stderr=errors,
    )

    assert result == 1
    assert "requires an EtherNetIP primary interface" in errors.getvalue()
    assert not destination.exists()


def test_gateway_report_returns_failure_for_missing_source(tmp_path: Path) -> None:
    errors = StringIO()

    result = main(
        (
            "gateway",
            "report",
            "--eds",
            str(tmp_path / "missing.eds"),
            "--gsd",
            str(tmp_path / "missing.gsd"),
            "--config",
            str(tmp_path / "missing.psj"),
            "--mapping",
            str(tmp_path / "missing.L5X"),
            "--output",
            str(tmp_path / "reports"),
        ),
        stderr=errors,
    )

    assert result == 1
    assert "cannot generate PLX50 mapping report" in errors.getvalue()
