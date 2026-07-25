"""Semantic validation for AutomationML references not enforced by CAEX XSD."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .automationml_elements import q
from .automationml_types import BASE_PLCOPEN_PATH
from .automationml_validation import AutomationMLValidationError


def validate_automationml_references(
    xml: str | bytes,
    document_path: str | Path,
) -> None:
    """Resolve class paths, IDs, links, and referenced PLCopen documents."""

    root = ET.fromstring(
        xml.encode("utf-8") if isinstance(xml, str) else xml
    )
    document = Path(document_path)
    available = _class_paths(root)
    for reference in root.findall(q("ExternalReference")):
        path = (document.parent / reference.attrib["Path"]).resolve()
        if not path.exists():
            raise AutomationMLValidationError(
                f"external AML reference does not exist: {path}"
            )
        external = ET.parse(path).getroot()
        alias = reference.attrib["Alias"]
        available.update(
            f"{alias}@{class_path}"
            for class_path in _class_paths(external)
        )
    _validate_class_references(root, available)
    known_ids = _validate_unique_ids(root)
    _validate_internal_links(root, known_ids)
    _validate_plcopen_references(root, document)


def _validate_class_references(
    root: ET.Element,
    available: set[str],
) -> None:
    reference_attributes = (
        "RefBaseClassPath",
        "RefBaseRoleClassPath",
        "RefAttributeType",
    )
    unresolved = sorted(
        {
            element.attrib[name]
            for element in root.iter()
            for name in reference_attributes
            if name in element.attrib
            and element.attrib[name] not in available
        }
    )
    if unresolved:
        raise AutomationMLValidationError(
            "unresolved AutomationML class references: "
            + ", ".join(unresolved)
        )


def _validate_unique_ids(root: ET.Element) -> set[str]:
    ids = [
        element.attrib["ID"]
        for element in root.iter()
        if "ID" in element.attrib
    ]
    if len(ids) != len(set(ids)):
        raise AutomationMLValidationError("duplicate CAEX IDs found")
    return set(ids)


def _validate_internal_links(
    root: ET.Element,
    known_ids: set[str],
) -> None:
    for link in root.iter(q("InternalLink")):
        for side in ("RefPartnerSideA", "RefPartnerSideB"):
            if link.attrib.get(side) not in known_ids:
                raise AutomationMLValidationError(
                    f"internal link {link.attrib.get('Name')!r} has "
                    f"unresolved endpoint {link.attrib.get(side)!r}"
                )


def _validate_plcopen_references(
    root: ET.Element,
    document: Path,
) -> None:
    for interface in root.iter(q("ExternalInterface")):
        if interface.attrib.get("RefBaseClassPath") != BASE_PLCOPEN_PATH:
            continue
        uri = interface.find(
            f"{q('Attribute')}[@Name='refURI']/{q('Value')}"
        )
        if uri is None or not uri.text:
            raise AutomationMLValidationError(
                "PLCopenXMLInterface is missing refURI"
            )
        target = (document.parent / uri.text).resolve()
        if not target.exists():
            raise AutomationMLValidationError(
                f"PLCopen XML reference does not exist: {target}"
            )


def _class_paths(root: ET.Element) -> set[str]:
    paths: set[str] = set()
    specifications = (
        ("InterfaceClassLib", "InterfaceClass"),
        ("RoleClassLib", "RoleClass"),
        ("SystemUnitClassLib", "SystemUnitClass"),
        ("AttributeTypeLib", "AttributeType"),
    )
    for library_name, class_name in specifications:
        for library in root.findall(q(library_name)):
            prefix = library.attrib["Name"]
            for class_element in library.findall(q(class_name)):
                _collect_class_paths(
                    class_element,
                    class_name,
                    prefix,
                    paths,
                )
    return paths


def _collect_class_paths(
    element: ET.Element,
    class_name: str,
    prefix: str,
    paths: set[str],
) -> None:
    path = f"{prefix}/{element.attrib['Name']}"
    paths.add(path)
    for child in element.findall(q(class_name)):
        _collect_class_paths(child, class_name, path, paths)
