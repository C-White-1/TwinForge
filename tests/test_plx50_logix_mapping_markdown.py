from twinforge.assembly import (
    Plx50LogixMappingResult,
    Plx50LogixPointCorrelation,
    Plx50LogixTransfer,
)
from twinforge.exporters import Plx50LogixMappingMarkdownExporter


def _result(*, unresolved: tuple[str, ...] = ()) -> Plx50LogixMappingResult:
    transfer = Plx50LogixTransfer(
        module_name="Gateway",
        direction="I",
        connection_number=1,
        assembly_offset=72,
        copy_length=1,
        controller_tag="Gateway_Device03.Input",
        source_text=(
            "CPS(Gateway:I1.Data[72],Gateway_Device03.Input,1)"
        ),
    )
    correlation = Plx50LogixPointCorrelation(
        station_address=3,
        slot_id=1,
        point_type="Input",
        point_name="Input4Bytes",
        data_type="REAL",
        byte_length=4,
        profibus_reference="station 3/slot 1/Input offset 0",
        controller_tag_path="Gateway_Device03.Input.Input4Bytes",
        assembly_reference="Gateway:I1.Data[72]",
        copy_length=1,
        evidence=(transfer.source_text,),
    )
    return Plx50LogixMappingResult(
        transfers=(transfer,),
        correlations=(correlation,),
        unresolved_points=unresolved,
        diagnostics=(),
    )


def test_exports_reviewable_point_and_transfer_tables() -> None:
    report = Plx50LogixMappingMarkdownExporter().export(_result())

    assert "- Correlated PROFIBUS points: 1" in report
    assert "<!-- markdownlint-disable MD013 -->" in report
    assert "PROFIBUS DP → EtherNet/IP" in report
    assert "`Gateway_Device03.Input.Input4Bytes`" in report
    assert "`Gateway:I1.Data[72]`" in report
    assert "| input | 1 |" in report
    assert "No unresolved PROFIBUS points." in report
    assert report.endswith("\n")


def test_preserves_unresolved_point_references() -> None:
    report = Plx50LogixMappingMarkdownExporter().export(
        _result(unresolved=("station 9/slot 2/Output offset 4",))
    )

    assert "- Unresolved PROFIBUS points: 1" in report
    assert "- `station 9/slot 2/Output offset 4`" in report
