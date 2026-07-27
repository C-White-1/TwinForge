from twinforge.analysis import analyze_cyclic_io_contract
from twinforge.exporters import CyclicIOContractMarkdownExporter
from twinforge.model import (
    AddOnInstruction,
    AddOnInstructionParameter,
    Connection,
    Controller,
    Datatype,
    DatatypeMember,
    Identity,
    Routine,
    StructuredTextLine,
    Tag,
)


def _fixture():
    controller = Controller(identity=Identity(), name="PLC")
    status = Datatype(
        name="StatusImage",
        members=[
            DatatypeMember(name="Word", data_type_name="INT"),
            DatatypeMember(
                name="Ready",
                data_type_name="BIT",
                target="Word",
                bit_number=0,
                description="Ready.",
            ),
            DatatypeMember(name="Feedback", data_type_name="INT"),
        ],
    )
    command = Datatype(
        name="CommandImage",
        members=[
            DatatypeMember(name="Word", data_type_name="INT"),
            DatatypeMember(
                name="Start",
                data_type_name="BIT",
                target="Word",
                bit_number=1,
                description="Start.",
            ),
            DatatypeMember(name="Reference", data_type_name="INT"),
        ],
    )
    local = Datatype(
        name="LocalData",
        members=[
            DatatypeMember(name="DataIn", data_type_name="StatusImage"),
            DatatypeMember(name="DataOut", data_type_name="CommandImage"),
        ],
    )
    for datatype in (status, command, local):
        controller.add_datatype(datatype)
    for datatype in controller.datatypes.values():
        for member in datatype.members:
            member.data_type = controller.get_datatype(
                member.data_type_name or ""
            )
    aoi = AddOnInstruction(name="Drive")
    aoi.add_parameter(
        AddOnInstructionParameter(
            name="Ref_DataIn", data_type="VendorInput"
        )
    )
    aoi.add_parameter(
        AddOnInstructionParameter(
            name="Ref_DataOut", data_type="VendorOutput"
        )
    )
    aoi.add_local_tag(Tag(name="Local", data_type="LocalData"))
    aoi.add_routine(
        Routine(
            name="Logic",
            language="ST",
            structured_text_lines=[
                StructuredTextLine(
                    text="COP(Ref_DataIn, Local.DataIn, 1);"
                ),
                StructuredTextLine(
                    text="COP(Local.DataOut, Ref_DataOut, 4);"
                ),
            ],
        )
    )
    connection = Connection(
        name="Cyclic",
        protocol="EtherNet/IP",
        input_connection_point=1,
        output_connection_point=2,
        input_size_bytes=4,
        output_size_bytes=4,
        requested_packet_interval_microseconds=10_000,
        unicast=True,
    )
    return controller, aoi, connection


def test_analyzes_overlay_layout_and_connection_contract():
    contract = analyze_cyclic_io_contract(*_fixture())

    assert contract.input_image.connection_point == 1
    assert contract.input_image.fields[1].overlay_target == "Word"
    assert contract.input_image.fields[1].bit_number == 0
    assert contract.input_image.fields[2].byte_offset == 2
    assert contract.output_image.fields[1].bit_number == 1
    assert contract.diagnostics == ()


def test_exports_cyclic_contract_as_markdown():
    contract = analyze_cyclic_io_contract(*_fixture())

    result = CyclicIOContractMarkdownExporter().export(contract)

    assert "- Requested packet interval: 10 ms" in result
    assert "| 0–1 | 0 | `Ready` | `BIT` | Ready. |" in result
    assert "| 2–3 | — | `Reference` | `INT` | — |" in result


def test_copy_count_uses_destination_element_size_not_bytes():
    controller, aoi, connection = _fixture()

    contract = analyze_cyclic_io_contract(controller, aoi, connection)

    assert contract.input_image.copied_size_bytes == 4
    assert contract.diagnostics == ()
