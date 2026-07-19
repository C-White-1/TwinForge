from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Literal

from twinforge.schema.l5x.spec import AttributeSpec, ElementSpec

ReportMode = Literal["summary", "debug"]


@dataclass
class CapturedSection:
    tag: str

    text: str | None = None

    tail: str | None = None

    known_attributes: set[str] = field(default_factory=set)

    attribute_specs: dict[str, AttributeSpec] = field(default_factory=dict)

    known_elements: set[str] = field(default_factory=set)

    element_specs: dict[str, ElementSpec] = field(default_factory=dict)

    attributes: dict[str, str] = field(default_factory=dict)

    elements: dict[str, list["CapturedSection"]] = field(default_factory=dict)

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
        known_attributes: set[str] | dict[str, AttributeSpec] | None = None,
        known_elements: set[str] | dict[str, ElementSpec] | None = None,
        *,
        mode: ReportMode = "summary",
        max_depth: int | None = 2,
        _depth: int = 0,
    ) -> None:
        if mode not in ("summary", "debug"):
            raise ValueError("report mode must be 'summary' or 'debug'")

        known_attribute_names = _spec_names(known_attributes, self.known_attributes)
        attribute_specs = (
            known_attributes
            if isinstance(known_attributes, dict)
            else self.attribute_specs
        )
        applicable_attribute_names = {
            name
            for name in known_attribute_names
            if _attribute_is_applicable(attribute_specs.get(name), self.attributes)
        }
        inapplicable_attribute_names = (
            known_attribute_names - applicable_attribute_names
        )
        known_element_names = _spec_names(known_elements, self.known_elements)
        element_specs = (
            known_elements if isinstance(known_elements, dict) else self.element_specs
        )
        indent = "  " * _depth
        child_indent = "  " * (_depth + 1)

        print(f"\n{indent}<{self.tag}>")

        present_attributes = []
        for name in sorted(known_attribute_names):
            if name in self.attributes:
                value = self.attributes[name]
                label = _attribute_value_label(attribute_specs.get(name), value)
                suffix = f" ({label})" if label is not None else ""
                present_attributes.append(f"{name}: {value}{suffix}")
        _print_group(
            "Documented attributes present",
            present_attributes,
            child_indent,
            always=mode == "debug",
        )

        if mode == "debug":
            absent_applicable = applicable_attribute_names - set(self.attributes)
            required_attributes = {
                name
                for name in absent_applicable
                if attribute_specs.get(name) is not None
                and attribute_specs[name].required
            }
            _print_group(
                "Required attributes missing",
                sorted(required_attributes),
                child_indent,
                always=True,
            )
            _print_group(
                "Optional attributes absent",
                sorted(absent_applicable - required_attributes),
                child_indent,
                always=True,
            )
            _print_group(
                "Documented attributes not applicable",
                sorted(inapplicable_attribute_names - set(self.attributes)),
                child_indent,
                always=True,
            )

        present_elements = [
            f"{name}: {len(self.elements[name])}"
            for name in sorted(known_element_names)
            if name in self.elements
        ]
        _print_group(
            "Documented elements present",
            present_elements,
            child_indent,
            always=mode == "debug",
        )

        if mode == "debug":
            absent_elements = known_element_names - set(self.elements)
            required_elements = {
                name
                for name in absent_elements
                if element_specs.get(name) is not None and element_specs[name].required
            }
            _print_group(
                "Required elements missing",
                sorted(required_elements),
                child_indent,
                always=True,
            )
            _print_group(
                "Optional elements absent",
                sorted(absent_elements - required_elements),
                child_indent,
                always=True,
            )

        _print_group(
            "Extra attributes",
            [f"{name}: {value}" for name, value in sorted(self.extra_attributes.items())],
            child_indent,
            always=mode == "debug",
        )
        _print_group(
            "Extra elements",
            [f"{name}: {len(elements)}" for name, elements in sorted(self.extra_elements.items())],
            child_indent,
            always=mode == "debug",
        )

        if max_depth is not None and _depth >= max_depth:
            if self.elements:
                print(f"{child_indent}Nested elements omitted at max depth {max_depth}.")
            return

        for name in sorted(self.elements):
            for child in self.elements[name]:
                if mode == "summary" and not child._has_summary_content():
                    continue
                child.report(mode=mode, max_depth=max_depth, _depth=_depth + 1)

    def _has_summary_content(self) -> bool:
        return bool(
            self.attributes
            or self.elements
            or self.extra_attributes
            or self.extra_elements
            or (self.text and self.text.strip())
        )


def capture_section(
    element: ET.Element,
    known_attributes: dict[str, AttributeSpec],
    known_elements: dict[str, ElementSpec],
) -> CapturedSection:

    section = CapturedSection(
        tag=element.tag,
        text=element.text,
        tail=element.tail,
        known_attributes=set(known_attributes),
        attribute_specs=dict(known_attributes),
        known_elements=set(known_elements),
        element_specs=dict(known_elements),
    )

    for key, value in element.attrib.items():
        if key in known_attributes:
            section.attributes[key] = value
        else:
            section.extra_attributes[key] = value

    for child in element:
        if child.tag in known_elements:
            child_spec = known_elements[child.tag]
            child_section = capture_section(
                child,
                child_spec.attributes,
                child_spec.elements,
            )
            section.elements.setdefault(child.tag, []).append(child_section)
        else:
            section.extra_elements.setdefault(child.tag, []).append(child)

    present = set(section.elements)

    section.missing_elements = sorted(set(known_elements) - present)

    return section


def _spec_names(
    value: set[str] | dict[str, AttributeSpec] | dict[str, ElementSpec] | None,
    default: set[str],
) -> set[str]:
    if value is None:
        return default
    return set(value)


def _attribute_is_applicable(
    spec: AttributeSpec | None,
    attributes: dict[str, str],
) -> bool:
    if spec is None:
        return True
    return all(
        attributes.get(condition_name) in accepted_values
        for condition_name, accepted_values in spec.applicable_when
    )


def _attribute_value_label(spec: AttributeSpec | None, value: str) -> str | None:
    if spec is None:
        return None
    for known_value, label in spec.value_labels:
        if str(known_value) == value:
            return label
    return None


def _print_group(
    heading: str,
    lines: list[str],
    indent: str,
    *,
    always: bool,
) -> None:
    if not lines and not always:
        return
    print(f"{indent}{heading}:")
    for line in lines:
        print(f"{indent}  {line}")
