"""Parse the conservative subset of Logix alias path components we model."""

from __future__ import annotations

import re


_COMPONENT = re.compile(r"^(?P<name>[^\[\]]+)(?:\[(?P<indices>\d+(?:,\d+)*)\])?$")


def parse_alias_component(text: str) -> tuple[str, tuple[int, ...]] | None:
    """Return a name and zero-based indices, or ``None`` for unknown syntax."""

    match = _COMPONENT.fullmatch(text)
    if match is None:
        return None
    indices = match.group("indices")
    return (
        match.group("name"),
        tuple(int(item) for item in indices.split(",")) if indices else (),
    )
