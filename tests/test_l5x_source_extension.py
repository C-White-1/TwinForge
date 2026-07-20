import xml.etree.ElementTree as ET

from twinforge.converters.l5x import (
    captured_to_source_extension,
    element_to_source_extension,
)
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x.spec import AttributeSpec, ElementSpec


def test_adapter_preserves_known_and_unknown_data_in_source_order():
    element = ET.fromstring(
        """
        <Module Name="DI_Slot2" FutureAttribute="keep">
            leading text
            <Known Value="1">known text</Known>
            <Future PreserveMe="yes">
                <Nested Data="keep too" />
            </Future>
            <Known Value="2" />
        </Module>
        """
    )
    section = capture_section(
        element,
        {"Name": AttributeSpec(name="Name", description="")},
        {
            "Known": ElementSpec(
                name="Known",
                attributes={"Value": AttributeSpec(name="Value", description="")},
                repeatable=True,
            )
        },
    )

    extension = captured_to_source_extension(section)

    assert extension.format == "l5x"
    assert extension.root.attributes == {
        "Name": "DI_Slot2",
        "FutureAttribute": "keep",
    }
    assert [child.name for child in extension.root.children] == [
        "Known",
        "Future",
        "Known",
    ]
    assert extension.root.children[0].text == "known text"
    assert extension.root.children[1].attributes == {"PreserveMe": "yes"}
    assert extension.root.children[1].children[0].attributes == {
        "Data": "keep too"
    }
    assert extension.root.children[2].attributes == {"Value": "2"}


def test_adapter_preserves_text_and_tail_content():
    element = ET.fromstring("<Root>before<Known />after</Root>")
    section = capture_section(
        element,
        {},
        {"Known": ElementSpec(name="Known")},
    )

    root = captured_to_source_extension(section).root

    assert root.text == "before"
    assert root.children[0].tail == "after"


def test_element_adapter_preserves_an_uncaptured_document_root():
    element = ET.fromstring(
        '<RSLogix5000Content Owner="Example"><Controller Name="Demo" /></RSLogix5000Content>'
    )

    extension = element_to_source_extension(element)

    assert extension.root.name == "RSLogix5000Content"
    assert extension.root.attributes == {"Owner": "Example"}
    assert extension.root.children[0].name == "Controller"
    assert extension.root.children[0].attributes == {"Name": "Demo"}
