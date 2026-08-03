"""Small target-neutral XML and IEC value helpers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from twinforge.model import Tag


def qualified_name(namespace: str, name: str) -> str:
    """Build an ElementTree expanded name."""

    return f"{{{namespace}}}{name}"


def variable_add_data(variable: ET.Element, namespace: str) -> ET.Element:
    """Return a variable's existing ``addData`` node or create one."""

    add_data = variable.find(qualified_name(namespace, "addData"))
    if add_data is None:
        add_data = ET.SubElement(
            variable,
            qualified_name(namespace, "addData"),
        )
    return add_data


def unique_portable_name(operand: str, existing_names: set[str]) -> str:
    """Create a deterministic IEC-safe name that does not collide."""

    base = "TF_" + re.sub(r"\W+", "_", operand).strip("_")
    if not base or base == "TF_":
        base = "TF_Operand"
    candidate = base
    suffix = 2
    while candidate in existing_names:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def milliseconds_duration(milliseconds: int) -> str:
    """Convert milliseconds to an ISO 8601 duration used by PLCopen tasks."""

    seconds = milliseconds / 1000
    return f"PT{seconds:g}S"


def milliseconds_time_literal(milliseconds: int) -> str:
    """Convert milliseconds to an IEC ``TIME`` literal."""

    return f"TIME#{milliseconds}ms"


def plcopen_scalar_value(tag: Tag) -> str:
    """Return the PLCopen lexical representation of a scalar tag value."""

    initial_value = tag.initial_value
    if initial_value is None:
        raise ValueError(f"tag {tag.name!r} has no initial value")
    if initial_value.data_type == "BOOL":
        return "TRUE" if initial_value.value else "FALSE"
    return initial_value.lexical_value


def decorated_member_integer(tag: Tag, member_name: str) -> int | None:
    """Read an integer member from retained decorated L5X tag data."""

    for extension in tag.source_extensions:
        if extension.format.lower() != "l5x":
            continue
        for data in extension.root.children:
            if (
                data.name != "Data"
                or data.attributes.get("Format") != "Decorated"
            ):
                continue
            for structure in data.children:
                if structure.name != "Structure":
                    continue
                for member in structure.children:
                    if (
                        member.name == "DataValueMember"
                        and member.attributes.get("Name") == member_name
                    ):
                        try:
                            return int(member.attributes["Value"])
                        except (KeyError, ValueError):
                            return None
    return None


def timer_member_integer(tag: Tag, member_name: str) -> int | None:
    """Read a decorated L5X timer member retained in source extensions."""

    return decorated_member_integer(tag, member_name)
