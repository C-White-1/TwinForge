from pathlib import Path

import pytest

from twinforge.analysis import (
    compare_codesys_visualizations,
    inventory_opaque_visualization_properties,
)
from twinforge.exporters import CodesysVisualizationOpaqueMarkdownExporter
from twinforge.parsers.codesys_native import CodesysNativeExportParser
from twinforge.parsers.codesys_native_profiles import (
    codesys_font_points,
    codesys_font_serialized_size,
    codesys_native_profile,
)


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
CUSTOM_FONT_VARIANT = SOURCE.parent / "38_run_button_custom_font.export"
STOP_CUSTOM_FONT_VARIANT = (
    SOURCE.parent / "39_run_button_custom_font_size.export"
)
RUN_CUSTOM_FONT_SIZE_VARIANT = (
    SOURCE.parent / "40_run_button_custom_font_size.export"
)
LOCAL_EVIDENCE = pytest.mark.skipif(
    not all(
        path.exists()
        for path in (
            SOURCE,
            ALIGNMENT_BASELINE,
            ALIGNMENT_VARIANT,
            ALIGNMENT_REPETITION,
            FONT_STYLE_VARIANT,
            FONT_STYLE_REPETITION,
            CUSTOM_FONT_VARIANT,
            STOP_CUSTOM_FONT_VARIANT,
            RUN_CUSTOM_FONT_SIZE_VARIANT,
        )
    ),
    reason="ignored local CODESYS differential exports are unavailable",
)

SYNTHETIC = """\
<ExportFile><StructuredView><Single>
<List2 Name="EntryList"><Single>
 <Single Name="MetaObject"><Single Name="Name">VISU_Test</Single></Single>
 <Single Name="Object"><Single Name="VisualElemList">
  <List Name="VisualElementList"><Single>
   <Single Name="VisualElemMemberList">
    <List Name="VisualElemMemberList">
     <Single><Single Name="Id">1649127785</Single>
      <Single Name="Value">10</Single></Single>
     <Single><Single Name="Id">2340015797</Single>
      <Single Name="Value">LEFT</Single></Single>
     <Single><Single Name="Id">3729828405</Single>
      <List Name="Value"><Single>
       <Single Name="CanonicalName">Font-Title</Single>
       <Single Name="FontName">Arial Narrow</Single>
       <Single Name="FontSize">38</Single>
      </Single></List></Single>
     <Single><Single Name="Id">999999</Single>
      <Single Name="Value">opaque</Single></Single>
    </List>
   </Single>
   <Single Name="VisualElementName">Button</Single>
   <Single Name="VisualElementIdentifier">Button_1</Single>
   <Single Name="VisualElementId">0</Single>
  </Single></List>
 </Single></Single>
</Single></List2>
<Single Name="ProfileName">CODESYS V3.5 SP22 Patch 2</Single>
</Single></StructuredView></ExportFile>
"""


def test_opaque_inventory_excludes_verified_profile_mappings():
    document = CodesysNativeExportParser().parse(SYNTHETIC)

    properties = inventory_opaque_visualization_properties(document)
    identifiers = {item.property_id for item in properties}

    assert len(properties) == 1
    assert sum(item.occurrences for item in properties) == 1
    assert "1649127785" not in identifiers
    assert "550940142" not in identifiers
    assert "2340015797" not in identifiers
    assert "3729828405" not in identifiers
    assert properties[0].property_id == "999999"


def test_opaque_report_preserves_evidence_without_guessed_names():
    document = CodesysNativeExportParser().parse(SYNTHETIC)
    properties = inventory_opaque_visualization_properties(document)

    report = CodesysVisualizationOpaqueMarkdownExporter().export(
        properties,
        profile=document.profile,
    )

    assert "- Unmapped property IDs: 1" in report
    assert "| `999999` | 1 |" in report
    assert "experiment candidates, not sufficient mapping evidence" in report


def test_checked_in_opaque_report_matches_baseline_evidence():
    report = (
        Path(__file__).parents[1]
        / "reports/Dev_PF525_Program/"
        "codesys_visualization_opaque_properties.md"
    ).read_text(encoding="utf-8")

    assert "# CODESYS opaque visualization-property register" in report
    assert "- Profile: CODESYS V3.5 SP22 Patch 2" in report
    assert "- Unmapped property IDs: 29" in report


@LOCAL_EVIDENCE
def test_local_opaque_report_matches_baseline_evidence():
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


@LOCAL_EVIDENCE
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


@LOCAL_EVIDENCE
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


@LOCAL_EVIDENCE
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


@LOCAL_EVIDENCE
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


@LOCAL_EVIDENCE
def test_experiment_38_establishes_explicit_custom_font_baseline():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(FONT_STYLE_REPETITION),
        parser.parse(CUSTOM_FONT_VARIANT),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_2"
    assert len(change.property_changes) == 1
    font = change.property_changes[0]
    assert font.property_name == "font"
    assert font.before is not None
    assert font.after is not None
    assert "CanonicalName=Font-Title" in font.before
    assert "; CanonicalName=" not in font.after
    assert "FontName=Arial" in font.after
    assert "DisplayName=Arial" in font.after
    assert "FontSize=19" in font.after


@LOCAL_EVIDENCE
def test_experiment_39_establishes_stop_button_custom_font_16():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(CUSTOM_FONT_VARIANT),
        parser.parse(STOP_CUSTOM_FONT_VARIANT),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_3"
    assert change.bindings_before == change.bindings_after
    assert change.actions_before == change.actions_after
    assert len(change.property_changes) == 1
    font = change.property_changes[0]
    assert font.property_name == "font"
    assert font.before is not None
    assert font.after is not None
    assert "CanonicalName=Font-Title" in font.before
    assert "FontName=Arial" in font.after
    assert "DisplayName=Arial" in font.after
    assert "FontSize=21" in font.after


def test_sp22_font_size_uses_verified_96_dpi_conversion():
    profile = codesys_native_profile("CODESYS V3.5 SP22 Patch 2")
    assert profile is not None

    assert codesys_font_points(19, profile) == 14.25
    assert codesys_font_points(21, profile) == 15.75
    assert codesys_font_serialized_size(14, profile) == 19
    assert codesys_font_serialized_size(16, profile) == 21


@LOCAL_EVIDENCE
def test_experiment_40_isolates_run_button_serialized_font_size():
    parser = CodesysNativeExportParser()

    result = compare_codesys_visualizations(
        parser.parse(STOP_CUSTOM_FONT_VARIANT),
        parser.parse(RUN_CUSTOM_FONT_SIZE_VARIANT),
    )

    assert result.manager_changes == ()
    assert len(result.element_changes) == 1
    change = result.element_changes[0]
    assert change.element_key == "GenElemInst_2"
    assert len(change.property_changes) == 1
    font = change.property_changes[0]
    assert font.property_name == "font"
    assert font.before is not None
    assert font.after is not None
    assert font.before.replace("FontSize=19", "FontSize=21") == font.after
