import pytest

from twinforge.analysis import CyclicIOContract, CyclicIOField, CyclicIOImage
from twinforge.runtime import (
    ByteOrder,
    ParameterOperation,
    ParameterRequest,
    ParameterResult,
    ParameterResultState,
    build_packed_cyclic_io_contract,
)


def _powerflex_contract() -> CyclicIOContract:
    status_fields = (
        CyclicIOField("Pad", "DINT", 0, 4),
        CyclicIOField("DriveStatus", "INT", 4, 2),
        CyclicIOField("Ready", "BIT", 4, 2, "DriveStatus", 0),
        CyclicIOField("Fault", "BIT", 4, 2, "DriveStatus", 7),
        CyclicIOField("OutputSpeed", "INT", 6, 2),
    )
    command_fields = (
        CyclicIOField("LogicCommand", "INT", 0, 2),
        CyclicIOField("Stop", "BIT", 0, 2, "LogicCommand", 0),
        CyclicIOField("Start", "BIT", 0, 2, "LogicCommand", 1),
        CyclicIOField("Reverse", "BIT", 0, 2, "LogicCommand", 5),
        CyclicIOField("SpeedCommand", "INT", 2, 2),
    )
    return CyclicIOContract(
        implementation_name="Dvc_PF525",
        protocol="EtherNet/IP",
        requested_packet_interval_microseconds=10_000,
        unicast=True,
        input_image=CyclicIOImage(
            "status",
            "Ref_DataIn",
            "AB:ETHERNET_MODULE_SINT_8Bytes:I:0",
            1,
            8,
            8,
            "Local.DataIn",
            status_fields,
        ),
        output_image=CyclicIOImage(
            "command",
            "Ref_DataOut",
            "AB:ETHERNET_MODULE_SINT_4Bytes:O:0",
            2,
            4,
            4,
            "Local.DataOut",
            command_fields,
        ),
    )


def test_builds_target_neutral_powerflex_layouts():
    packed = build_packed_cyclic_io_contract(_powerflex_contract())

    assert packed.input_layout.byte_size == 8
    assert packed.output_layout.byte_size == 4
    assert packed.input_layout.byte_order is ByteOrder.LITTLE
    assert packed.input_layout.fields[2].overlay_target == "DriveStatus"


def test_decodes_status_bits_and_signed_feedback():
    packed = build_packed_cyclic_io_contract(_powerflex_contract())

    decoded = packed.input_layout.decode(
        bytes.fromhex("7856341281009cff")
    )

    assert decoded.values["Pad"] == 0x12345678
    assert decoded.values["DriveStatus"] == 0x0081
    assert decoded.values["Ready"] is True
    assert decoded.values["Fault"] is True
    assert decoded.values["OutputSpeed"] == -100
    assert decoded.raw == bytes.fromhex("7856341281009cff")


def test_encodes_command_bits_and_speed_without_losing_base_bits():
    packed = build_packed_cyclic_io_contract(_powerflex_contract())

    encoded = packed.output_layout.encode(
        {"Start": True, "Reverse": True, "SpeedCommand": 5000},
        base=bytes.fromhex("01000000"),
    )

    assert encoded == bytes.fromhex("23008813")
    decoded = packed.output_layout.decode(encoded)
    assert decoded.values["Stop"] is True
    assert decoded.values["Start"] is True
    assert decoded.values["Reverse"] is True
    assert decoded.values["SpeedCommand"] == 5000


def test_rejects_wrong_image_size_and_unknown_fields():
    layout = build_packed_cyclic_io_contract(
        _powerflex_contract()
    ).output_layout

    with pytest.raises(ValueError, match="requires 4 bytes"):
        layout.decode(b"\x00")
    with pytest.raises(ValueError, match="unknown packed fields"):
        layout.encode({"NotAField": 1})


def test_parameter_contract_enforces_read_and_write_semantics():
    read = ParameterRequest(ParameterOperation.READ, 143)
    write = ParameterRequest(ParameterOperation.WRITE, 144, 0)
    failed = ParameterResult(
        ParameterResultState.FAILED,
        error_code="timeout",
        error_message="No response",
    )

    assert read.value is None
    assert write.value == 0
    assert failed.error_code == "timeout"
    with pytest.raises(ValueError, match="write request requires"):
        ParameterRequest(ParameterOperation.WRITE, 143)
    with pytest.raises(ValueError, match="read request must not"):
        ParameterRequest(ParameterOperation.READ, 143, 1)
