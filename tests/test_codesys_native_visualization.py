from dataclasses import replace

import pytest

from twinforge.exporters.codesys_visualization_markdown import (
    CodesysVisualizationMarkdownExporter,
)
from twinforge.analysis.codesys_visualization_diff import (
    compare_codesys_visualizations,
)
from twinforge.converters.codesys_visualization import (
    convert_codesys_visualization,
)
from twinforge.exporters.codesys_visualization_diff_markdown import (
    CodesysVisualizationDiffMarkdownExporter,
)
from twinforge.exporters.codesys_native_visualization import (
    CodesysNativeVisualizationExporter,
    CodesysNativeVisualizationExportError,
)
from twinforge.parsers.codesys_native import CodesysNativeExportParser
from twinforge.model import (
    VisualizationBinding,
    VisualizationBindingRole,
    VisualizationControlKind,
    VisualizationDocument,
    VisualizationGeometry,
    VisualizationInteraction,
    VisualizationInteractionKind,
)


XML = """\
<ExportFile><StructuredView><Single>
<List2 Name="EntryList">
 <Single><Single Name="MetaObject"><Single Name="Name">Visualization Manager</Single></Single>
  <Single Name="Object"><Single Name="VisuStyle">Basic style</Single>
  <Single Name="NumpadDialog">VisuDialogs.NumPad2</Single></Single></Single>
 <Single><Single Name="MetaObject"><Single Name="Name">VISU_Test</Single></Single>
  <Single Name="Object"><Single Name="VisualElemList">
   <List Name="VisualElementList"><Single>
    <Array Name="ConfiguredComplexInputs"><Single>
     <Single Name="Name">Toggle</Single>
     <Single Name="Value">PLC_PRG.xRun</Single>
    </Single></Array>
    <Single Name="VisualElemMemberList"><List Name="VisualElemMemberList">
     <Single><Single Name="Id">1649127785</Single><Single Name="Value">10</Single></Single>
     <Single><Single Name="Id">357335551</Single><Single Name="Value">20</Single></Single>
     <Single><Single Name="Id">2422045748</Single><Single Name="Value">100</Single></Single>
     <Single><Single Name="Id">2134141914</Single><Single Name="Value">30</Single></Single>
     <Single><Single Name="Id">390574330</Single><Single Name="Value">Run</Single></Single>
    </List></Single>
    <Single Name="VisualElementName">Button</Single>
    <Single Name="VisualElementIdentifier">Button_1</Single>
    <Single Name="VisualElementId">0</Single>
   </Single></List>
  </Single><Single Name="VisuSizeManager"><Single><Single Name="Width">454</Single>
  <Single Name="Height">299</Single></Single></Single></Single></Single>
</List2><Single Name="ProfileName">CODESYS V3.5 SP22 Patch 2</Single>
</Single></StructuredView></ExportFile>
"""


def test_parser_preserves_archive_and_decodes_supported_inventory() -> None:
    result = CodesysNativeExportParser().parse(XML)

    assert result.profile == "CODESYS V3.5 SP22 Patch 2"
    assert result.profile_mappings_applied
    assert result.source_xml == XML
    assert result.managers[0].numpad == "VisuDialogs.NumPad2"
    visualization = result.visualizations[0]
    assert (visualization.width, visualization.height) == (454, 299)
    element = visualization.elements[0]
    assert element.properties["text"] == "Run"
    assert element.bindings == ("PLC_PRG.xRun",)
    assert element.actions[0].kind == "Toggle"
    assert "VisualElemMemberList" in element.raw_xml


def test_parser_exposes_confirmed_profile_property_mappings() -> None:
    xml = XML.replace(
        "</List></Single>",
        "<Single><Single Name=\"Id\">550940142</Single>"
        "<Single Name=\"Value\">60</Single></Single>"
        "<Single><Single Name=\"Id\">1473355128</Single>"
        "<Single Name=\"Value\">35</Single></Single>"
        "<Single><Single Name=\"Id\">2340015797</Single>"
        "<Single Name=\"Value\">LEFT</Single></Single>"
        "<Single><Single Name=\"Id\">2565699834</Single>"
        "<Single Name=\"Value\">TOP</Single></Single>"
        "<Single><Single Name=\"Id\">3729828405</Single>"
        "<Single Name=\"Value\">Font-Standard</Single></Single>"
        "</List></Single>",
        1,
    )

    element = (
        CodesysNativeExportParser()
        .parse(xml)
        .visualizations[0]
        .elements[0]
    )

    assert element.properties["center_x"] == "60"
    assert element.property_names["550940142"] == "center_x"
    assert element.properties["center_y"] == "35"
    assert element.property_names["1473355128"] == "center_y"
    assert element.properties["horizontal_alignment"] == "LEFT"
    assert (
        element.property_names["2340015797"] == "horizontal_alignment"
    )
    assert element.properties["vertical_alignment"] == "TOP"
    assert element.property_names["2565699834"] == "vertical_alignment"
    assert element.properties["font"] == "Font-Standard"
    assert element.property_names["3729828405"] == "font"


def test_unknown_profile_preserves_numeric_members_without_decoding() -> None:
    unknown_xml = XML.replace(
        "CODESYS V3.5 SP22 Patch 2",
        "CODESYS V3.5 SP99",
    )

    result = CodesysNativeExportParser().parse(unknown_xml)
    element = result.visualizations[0].elements[0]

    assert not result.profile_mappings_applied
    assert element.properties == {}
    assert element.property_names == {}
    assert element.numeric_properties["1649127785"] == "10"
    assert element.numeric_properties["390574330"] == "Run"
    assert "VisualElemMemberList" in element.raw_xml


def test_converter_builds_vendor_neutral_control_and_preserves_source() -> None:
    parsed = CodesysNativeExportParser().parse(XML)

    document = convert_codesys_visualization(parsed)

    assert document.theme == "Basic style"
    assert document.source_extensions[0].root.name == "ExportFile"
    canvas = document.canvases[0]
    assert (canvas.name, canvas.width, canvas.height) == (
        "VISU_Test",
        454,
        299,
    )
    control = canvas.controls[0]
    assert control.kind is VisualizationControlKind.BUTTON
    assert (control.geometry.x, control.geometry.y) == (10, 20)
    assert control.text == "Run"
    assert control.bindings[0].role is VisualizationBindingRole.COMMAND
    assert (
        control.interactions[0].kind
        is VisualizationInteractionKind.TOGGLE
    )
    extension = control.source_extensions[0]
    assert extension.format == "codesys-native"
    assert extension.metadata["numeric_properties"]["1649127785"] == "10"


def test_converter_normalizes_input_box_constraints_and_roles() -> None:
    input_box = XML.replace(
        '<Array Name="ConfiguredComplexInputs"><Single>',
        '<Dictionary Name="VisualElementInputActions"><Entry><Value><Array>'
        '<Single><Single Name="InputBoxVariable">PLC_PRG.rSpeed</Single>'
        '<Single Name="InputBoxMin">0</Single>'
        '<Single Name="InputBoxMax">65</Single>'
        '<Single Name="InputBoxDialogTitle">Speed</Single>'
        '<Single Name="Format">%.1f</Single></Single></Array></Value></Entry>'
        "</Dictionary><Array Name=\"ConfiguredComplexInputs\"><Single>",
    )

    control = (
        convert_codesys_visualization(
            CodesysNativeExportParser().parse(input_box)
        )
        .canvases[0]
        .controls[0]
    )

    roles = {
        binding.expression: binding.role for binding in control.bindings
    }
    assert roles["PLC_PRG.xRun"] is VisualizationBindingRole.COMMAND
    assert roles["PLC_PRG.rSpeed"] is VisualizationBindingRole.INPUT
    value_input = next(
        interaction
        for interaction in control.interactions
        if interaction.kind is VisualizationInteractionKind.VALUE_INPUT
    )
    assert (
        value_input.operand,
        value_input.minimum,
        value_input.maximum,
        value_input.value_format,
        value_input.prompt,
    ) == ("PLC_PRG.rSpeed", "0", "65", "%.1f", "Speed")


def test_unknown_profile_conversion_remains_lossless_but_unpositioned() -> None:
    unknown_xml = XML.replace(
        "CODESYS V3.5 SP22 Patch 2",
        "CODESYS V3.5 SP99",
    )

    control = (
        convert_codesys_visualization(
            CodesysNativeExportParser().parse(unknown_xml)
        )
        .canvases[0]
        .controls[0]
    )

    assert control.geometry.x is None
    extension = control.source_extensions[0]
    assert extension.metadata["profile_mappings_applied"] is False
    assert extension.metadata["numeric_properties"]["1649127785"] == "10"


def test_source_backed_export_updates_only_verified_portable_fields() -> None:
    source_xml = XML.replace(
        "</List></Single>",
        "<Single><Single Name=\"Id\">550940142</Single>"
        "<Single Name=\"Value\">60</Single></Single>"
        "<Single><Single Name=\"Id\">1473355128</Single>"
        "<Single Name=\"Value\">35</Single></Single>"
        "<Single><Single Name=\"Id\">999999</Single>"
        "<Single Name=\"Value\">opaque</Single></Single>"
        "</List></Single>",
        1,
    )
    document = convert_codesys_visualization(
        CodesysNativeExportParser().parse(source_xml)
    )
    control = document.canvases[0].controls[0]
    control.geometry = VisualizationGeometry(20, 30, 120, 40)
    control.text = "Start"
    control.interactions[0] = VisualizationInteraction(
        kind=VisualizationInteractionKind.TOGGLE,
        operand="PLC_PRG.xStart",
    )
    control.bindings[0] = VisualizationBinding(
        expression="PLC_PRG.xStart",
        role=VisualizationBindingRole.COMMAND,
    )

    result = CodesysNativeVisualizationExporter().export(document)
    exported = CodesysNativeExportParser().parse(result.xml)
    exported_control = exported.visualizations[0].elements[0]

    assert result.profile == "CODESYS V3.5 SP22 Patch 2"
    assert exported_control.properties == {
        "x": "20",
        "y": "30",
        "width": "120",
        "height": "40",
        "text": "Start",
        "center_x": "80",
        "center_y": "50",
    }
    assert exported_control.bindings == ("PLC_PRG.xStart",)
    assert exported_control.numeric_properties["999999"] == "opaque"


def test_native_export_rejects_document_without_source_archive() -> None:
    with pytest.raises(
        CodesysNativeVisualizationExportError,
        match="retained CODESYS ExportFile",
    ):
        CodesysNativeVisualizationExporter().export(
            VisualizationDocument()
        )


def test_source_backed_export_updates_input_box_constraints() -> None:
    source_xml = (
        XML.replace(
            "</List></Single>",
            "<Single><Single Name=\"Id\">550940142</Single>"
            "<Single Name=\"Value\">60</Single></Single>"
            "<Single><Single Name=\"Id\">1473355128</Single>"
            "<Single Name=\"Value\">35</Single></Single>"
            "</List></Single>",
            1,
        )
        .replace(
            '<Array Name="ConfiguredComplexInputs"><Single>',
            '<Dictionary Name="VisualElementInputActions"><Entry><Value>'
            '<Array><Single>'
            '<Single Name="InputBoxVariable">PLC_PRG.rSpeed</Single>'
            '<Single Name="InputBoxMin">0</Single>'
            '<Single Name="InputBoxMax">65</Single>'
            '<Single Name="InputBoxDialogTitle">Speed</Single>'
            '<Single Name="Format">%.1f</Single>'
            "</Single></Array></Value></Entry></Dictionary>"
            '<Array Name="ConfiguredComplexInputs"><Single>',
        )
    )
    document = convert_codesys_visualization(
        CodesysNativeExportParser().parse(source_xml)
    )
    control = document.canvases[0].controls[0]
    input_index = next(
        index
        for index, interaction in enumerate(control.interactions)
        if interaction.kind is VisualizationInteractionKind.VALUE_INPUT
    )
    control.interactions[input_index] = replace(
        control.interactions[input_index],
        maximum="70",
    )

    result = CodesysNativeVisualizationExporter().export(document)
    exported = CodesysNativeExportParser().parse(result.xml)
    input_box = next(
        action
        for action in exported.visualizations[0].elements[0].actions
        if action.kind == "InputBox"
    )

    assert input_box.properties["InputBoxMin"] == "0"
    assert input_box.properties["InputBoxMax"] == "70"
    assert input_box.properties["Format"] == "%.1f"
    assert input_box.properties["InputBoxDialogTitle"] == "Speed"


def test_native_export_sets_required_prompt_initialization_flag() -> None:
    source_xml = (
        XML.replace(
            "</List></Single>",
            "<Single><Single Name=\"Id\">550940142</Single>"
            "<Single Name=\"Value\">60</Single></Single>"
            "<Single><Single Name=\"Id\">1473355128</Single>"
            "<Single Name=\"Value\">35</Single></Single>"
            "</List></Single>",
            1,
        )
        .replace(
            '<Array Name="ConfiguredComplexInputs"><Single>',
            '<Dictionary Name="VisualElementInputActions"><Entry><Value>'
            '<Array><Single>'
            '<Single Name="InputBoxVariable">PLC_PRG.rSpeed</Single>'
            '<Single Name="InputBoxMin">0</Single>'
            '<Single Name="InputBoxMax">70</Single>'
            '<Single Name="InputBoxDialogTitle">Speed</Single>'
            '<Single Name="TextOutputVariableInitialized">False</Single>'
            '<Single Name="Format">%.1f</Single>'
            "</Single></Array></Value></Entry></Dictionary>"
            '<Array Name="ConfiguredComplexInputs"><Single>',
        )
    )
    document = convert_codesys_visualization(
        CodesysNativeExportParser().parse(source_xml)
    )
    control = document.canvases[0].controls[0]
    input_index = next(
        index
        for index, interaction in enumerate(control.interactions)
        if interaction.kind is VisualizationInteractionKind.VALUE_INPUT
    )
    control.interactions[input_index] = replace(
        control.interactions[input_index],
        prompt="TwinForge Speed",
    )

    result = CodesysNativeVisualizationExporter().export(document)
    exported = CodesysNativeExportParser().parse(result.xml)
    input_box = next(
        action
        for action in exported.visualizations[0].elements[0].actions
        if action.kind == "InputBox"
    )

    assert input_box.properties["InputBoxDialogTitle"] == "TwinForge Speed"
    assert input_box.properties["TextOutputVariableInitialized"] == "True"


def test_markdown_reports_generation_boundary() -> None:
    result = CodesysNativeExportParser().parse(XML)
    report = CodesysVisualizationMarkdownExporter().export(result)

    assert "| 0 | Button_1 | Button | 10,20 100×30 | Run |" in report
    assert "|  |" not in report
    assert "does not yet generate this format" in report


def test_diff_reports_known_and_opaque_property_changes() -> None:
    parser = CodesysNativeExportParser()
    changed = (
        XML.replace(
            '<Single Name="Value">10</Single>',
            '<Single Name="Value">15</Single>',
            1,
        )
        .replace(
            '<Single Name="Value">Run</Single>',
            '<Single Name="Value">Start</Single>',
            1,
        )
        .replace("PLC_PRG.xRun", "PLC_PRG.xStart")
    )

    result = compare_codesys_visualizations(
        parser.parse(XML),
        parser.parse(changed),
    )

    assert len(result.element_changes) == 1
    element = result.element_changes[0]
    assert element.element_key == "Button_1"
    assert element.bindings_after == ("PLC_PRG.xStart",)
    assert {
        (change.property_id, change.property_name)
        for change in element.property_changes
    } == {
        ("1649127785", "x"),
        ("390574330", "text"),
    }
    report = CodesysVisualizationDiffMarkdownExporter().export(result)
    assert "| 1649127785 | x | 10 | 15 |" in report
    assert "| 390574330 | text | Run | Start |" in report
    assert "|  |" not in report


def test_diff_detects_self_describing_action_property_change() -> None:
    parser = CodesysNativeExportParser()
    input_box = XML.replace(
        '<Array Name="ConfiguredComplexInputs"><Single>',
        '<Dictionary Name="VisualElementInputActions"><Entry><Value><Array>'
        '<Single><Single Name="InputBoxVariable">PLC_PRG.rSpeed</Single>'
        '<Single Name="Format">%.2f</Single></Single></Array></Value></Entry>'
        "</Dictionary><Array Name=\"ConfiguredComplexInputs\"><Single>",
    )
    changed = input_box.replace("%.2f", "%.1f")

    result = compare_codesys_visualizations(
        parser.parse(input_box),
        parser.parse(changed),
    )

    assert len(result.element_changes) == 1
    element = result.element_changes[0]
    assert "Format=%.2f" in element.action_details_before[1]
    assert "Format=%.1f" in element.action_details_after[1]
    assert [
        (
            change.action,
            change.property_name,
            change.before,
            change.after,
        )
        for change in element.action_property_changes
    ] == [("InputBox", "Format", "%.2f", "%.1f")]
    report = CodesysVisualizationDiffMarkdownExporter().export(result)
    assert "| InputBox | Format | %.2f | %.1f |" in report
