from pathlib import Path

from twinforge.analysis import (
    compare_codesys_visualizations,
    inventory_opaque_visualization_properties,
)
from twinforge.exporters import CodesysVisualizationOpaqueMarkdownExporter
from twinforge.parsers.codesys_native import CodesysNativeExportParser


SOURCE = (
    Path(__file__).parents[1]
    / "reference/PLCopenXML/codesys-native/24_stop_button_y.export"
)
ALIGNMENT_BASELINE = SOURCE.parent / "34_alignment_editor_baseline.export"
ALIGNMENT_VARIANT = (
    SOURCE.parent / "34_run_button_horizontal_alignment.export"
)
ALIGNMENT_REPETITION = (
    SOURCE.parent / "35_stop_button_horizontal_alignment.export"
)
FONT_STYLE_VARIANT = SOURCE.parent / "36_run_button_font_style.export"
FONT_STYLE_REPETITION = SOURCE.parent / "37_stop_button_font_style.export"


def test_opaque_inventory_excludes_verified_profile_mappings():
    document = CodesysNativeExportParser().parse(SOURCE)

    properties = inventory_opaque_visualization_properties(document)
    identifiers = {item.property_id for item in properties}

    assert len(properties) == 29
    assert sum(item.occurrences for item in properties) == 130
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

    assert "- Unmapped property IDs: 29" in report
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


def test_experiment_34_isolated_run_button_horizontal_alignment():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(ALIGNMENT_BASELINE),
        parser.parse(ALIGNMENT_VARIANT),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_2"
    assert change.bindings_before == change.bindings_after
    assert change.actions_before == change.actions_after
    assert [
        (
            item.property_id,
            item.property_name,
            item.before,
            item.after,
        )
        for item in change.property_changes
    ] == [
        (
            "2340015797",
            "horizontal_alignment",
            "HCENTER",
            "LEFT",
        )
    ]


def test_experiment_35_confirms_stop_button_horizontal_alignment():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(ALIGNMENT_VARIANT),
        parser.parse(ALIGNMENT_REPETITION),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_3"
    assert change.bindings_before == change.bindings_after
    assert change.actions_before == change.actions_after
    assert [
        (
            item.property_id,
            item.property_name,
            item.before,
            item.after,
        )
        for item in change.property_changes
    ] == [
        (
            "2340015797",
            "horizontal_alignment",
            "HCENTER",
            "LEFT",
        )
    ]


def test_experiment_36_exposes_structured_font_style_evidence():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(ALIGNMENT_REPETITION),
        parser.parse(FONT_STYLE_VARIANT),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_2"
    assert {
        item.property_id for item in change.property_changes
    } == {"663104332", "3729828405"}
    font = next(
        item
        for item in change.property_changes
        if item.property_id == "3729828405"
    )
    assert font.property_name == "font"
    assert font.before is not None
    assert font.after is not None
    assert "CanonicalName=Font-Standard" in font.before
    assert "FontName=Arial; " in font.before
    assert "FontSize=12" in font.before
    assert "CanonicalName=Font-Title" in font.after
    assert "FontName=Arial Narrow" in font.after
    assert "FontSize=38" in font.after


def test_experiment_37_confirms_structured_font_on_stop_button():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(FONT_STYLE_VARIANT),
        parser.parse(FONT_STYLE_REPETITION),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_3"
    assert change.bindings_before == change.bindings_after
    assert change.actions_before == change.actions_after
    assert len(change.property_changes) == 1
    font = change.property_changes[0]
    assert font.property_id == "3729828405"
    assert font.property_name == "font"
    assert font.before is not None
    assert font.after is not None
    assert "CanonicalName=Font-Standard" in font.before
    assert "CanonicalName=Font-Title" in font.after
