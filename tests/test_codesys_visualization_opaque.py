from pathlib import Path

from twinforge.analysis import inventory_opaque_visualization_properties
from twinforge.exporters import CodesysVisualizationOpaqueMarkdownExporter
from twinforge.parsers.codesys_native import CodesysNativeExportParser


SOURCE = (
    Path(__file__).parents[1]
    / "reference/PLCopenXML/codesys-native/24_stop_button_y.export"
)


def test_opaque_inventory_excludes_verified_profile_mappings():
    document = CodesysNativeExportParser().parse(SOURCE)

    properties = inventory_opaque_visualization_properties(document)
    identifiers = {item.property_id for item in properties}

    assert len(properties) == 31
    assert sum(item.occurrences for item in properties) == 143
    assert "1649127785" not in identifiers
    assert "550940142" not in identifiers
    assert properties[0].occurrences == 7


def test_opaque_report_preserves_evidence_without_guessed_names():
    document = CodesysNativeExportParser().parse(SOURCE)
    properties = inventory_opaque_visualization_properties(document)

    report = CodesysVisualizationOpaqueMarkdownExporter().export(
        properties,
        profile=document.profile,
    )

    assert "- Unmapped property IDs: 31" in report
    assert "| `823443203` | 5 |" in report
    assert "experiment candidates, not sufficient mapping evidence" in report


def test_checked_in_opaque_report_matches_baseline_evidence():
    document = CodesysNativeExportParser().parse(SOURCE)
    properties = inventory_opaque_visualization_properties(document)
    expected = CodesysVisualizationOpaqueMarkdownExporter().export(
        properties,
        profile=document.profile,
    )
    report = (
        Path(__file__).parents[1]
        / "reports/Dev_PF525_Program/"
        "codesys_visualization_opaque_properties.md"
    ).read_text(encoding="utf-8")

    assert report == expected
