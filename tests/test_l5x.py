import unittest
import xml.etree.ElementTree as ET

from twinforge.parsers.l5x.capture import CapturedSection, capture_section
from twinforge.schema.l5x import CONTROLLER_ELEMENTS
from twinforge.schema.l5x.spec import AttributeSpec, ElementSpec


class CaptureSectionTests(unittest.TestCase):
    def test_captures_known_child_sections_recursively(self):
        element = ET.fromstring(
            """
            <Root Name="Example">
                <Known Enabled="true">
                    <Nested Value="42">payload</Nested>
                </Known>
            </Root>
            """
        )
        known_attributes = {"Name": AttributeSpec(name="Name", description="")}
        known_elements = {
            "Known": ElementSpec(
                name="Known",
                attributes={
                    "Enabled": AttributeSpec(name="Enabled", description=""),
                },
                elements={
                    "Nested": ElementSpec(
                        name="Nested",
                        attributes={
                            "Value": AttributeSpec(name="Value", description=""),
                        },
                        content_type="text",
                    ),
                },
            ),
        }

        section = capture_section(element, known_attributes, known_elements)

        self.assertEqual(section.attributes, {"Name": "Example"})
        known = section.elements["Known"][0]
        self.assertIsInstance(known, CapturedSection)
        self.assertEqual(known.attributes, {"Enabled": "true"})

        nested = known.elements["Nested"][0]
        self.assertEqual(nested.attributes, {"Value": "42"})
        self.assertEqual(nested.text, "payload")

    def test_preserves_unknown_attributes_and_elements_at_each_level(self):
        element = ET.fromstring(
            """
            <Root KnownAttr="yes" ExtraRootAttr="keep">
                <Known ExtraKnownAttr="keep">
                    <UnexpectedChild PreserveMe="yes" />
                </Known>
                <UnexpectedRootChild PreserveMe="yes" />
            </Root>
            """
        )
        known_attributes = {
            "KnownAttr": AttributeSpec(name="KnownAttr", description=""),
        }
        known_elements = {
            "Known": ElementSpec(name="Known"),
        }

        section = capture_section(element, known_attributes, known_elements)

        self.assertEqual(section.extra_attributes, {"ExtraRootAttr": "keep"})
        self.assertIn("UnexpectedRootChild", section.extra_elements)
        self.assertEqual(
            section.extra_elements["UnexpectedRootChild"][0].attrib,
            {"PreserveMe": "yes"},
        )

        known = section.elements["Known"][0]
        self.assertEqual(known.extra_attributes, {"ExtraKnownAttr": "keep"})
        self.assertIn("UnexpectedChild", known.extra_elements)
        self.assertEqual(
            known.extra_elements["UnexpectedChild"][0].attrib,
            {"PreserveMe": "yes"},
        )

    def test_controller_security_primary_action_sets_are_nested_sections(self):
        element = ET.fromstring(
            """
            <Controller Use="Target" Name="Demo">
                <Security Code="0">
                    <PrimaryActionSets>
                        <PrimaryActionSet PermissionSet="Guest" IsPermissionSet="true">
                            encoded_permissions
                        </PrimaryActionSet>
                    </PrimaryActionSets>
                </Security>
            </Controller>
            """
        )

        section = capture_section(element, {}, CONTROLLER_ELEMENTS)

        security = section.elements["Security"][0]
        action_sets = security.elements["PrimaryActionSets"][0]
        action_set = action_sets.elements["PrimaryActionSet"][0]

        self.assertEqual(security.attributes, {"Code": "0"})
        self.assertEqual(
            action_set.attributes,
            {"PermissionSet": "Guest", "IsPermissionSet": "true"},
        )
        self.assertIn("encoded_permissions", action_set.text)


if __name__ == "__main__":
    unittest.main()
