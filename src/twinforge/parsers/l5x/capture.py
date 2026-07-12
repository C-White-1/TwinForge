from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from twinforge.schema.l5x.spec import AttributeSpec, ElementSpec


@dataclass
class CapturedSection:
    tag: str

    attributes: dict[str, str] = field(default_factory=dict)

    elements: dict[str, list[ET.Element]] = field(default_factory=dict)

    extra_attributes: dict[str, str] = field(default_factory=dict)

    extra_elements: dict[str, list[ET.Element]] = field(default_factory=dict)

    missing_elements: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{self.tag} "
            f"[{len(self.attributes)} attrs, "
            f"{len(self.elements)} elements, "
            f"{len(self.extra_attributes)} extra attrs, "
            f"{len(self.extra_elements)} extra elements]"
        )

    def report(
        self,
        known_attributes: set[str],
        known_elements: set[str],
    ) -> None:

        print(f"\n<{self.tag}>")

        print("\nDocumented attributes present:")
        for name in sorted(known_attributes):
            if name in self.attributes:
                print(f"  {name}: {self.attributes[name]}")

        print("\nDocumented attributes missing:")
        for name in sorted(known_attributes):
            if name not in self.attributes:
                print(f"  {name}")

        print("\nDocumented elements present:")
        for name in sorted(known_elements):
            if name in self.elements:
                print(f"  {name}: {len(self.elements[name])}")

        print("\nDocumented elements missing:")
        for name in sorted(known_elements):
            if name not in self.elements:
                print(f"  {name}")

        print("\nExtra attributes:")
        for name, value in sorted(self.extra_attributes.items()):
            print(f"  {name}: {value}")

        print("\nExtra elements:")
        for name, elements in sorted(self.extra_elements.items()):
            print(f"  {name}: {len(elements)}")


def capture_section(
    element: ET.Element,
    known_attributes: dict[str, AttributeSpec],
    known_elements: dict[str, ElementSpec],
) -> CapturedSection:

    section = CapturedSection(tag=element.tag)

    for key, value in element.attrib.items():
        if key in known_attributes:
            section.attributes[key] = value
        else:
            section.extra_attributes[key] = value

    for child in element:
        target = (
            section.elements if child.tag in known_elements else section.extra_elements
        )
        target.setdefault(child.tag, []).append(child)

    present = set(section.elements)

    section.missing_elements = sorted(set(known_elements) - present)

    return section
