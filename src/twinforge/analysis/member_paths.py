"""Resolve indexed/member/bit-select expressions against proven type definitions.

A path such as ``Pump.STAT[2].5`` is resolved only when every step is proven
by a captured definition: the base is a declared symbol, each ``.name`` is a
unique member of a structured (DDT) or Function Block type, each ``[n]`` is an
integer literal inside the declared array bounds, and each ``.n`` is a bit of a
fixed-width integer type. Anything else is left unresolved rather than guessed;
no execution, memory-effect or type-compatibility claim is made.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from twinforge.model.datatype import Datatype
from twinforge.model.graphical import MemberPath
from twinforge.model.library_interface import LibraryInterface

# Bit width of the integer types a ".n" bit select is accepted on. Corpus
# evidence (e.g. "_fault.0" on a WORD) supports the form; the width table is
# the fixed IEC 61131-3 size of each type.
BIT_WIDTHS: dict[str, int] = {
    "BYTE": 8, "WORD": 16, "DWORD": 32, "INT": 16, "UINT": 16, "DINT": 32, "UDINT": 32,
}


@dataclass
class _Type:
    name: str
    bounds: tuple[int, int] | None = None
    datatype: Datatype | None = None


@dataclass(frozen=True)
class MemberPathResult:
    status: str  # resolved | index_out_of_bounds | unresolved
    path: MemberPath | None = None
    detail: str = ""


def _split(expression: str, identifier: str) -> tuple[str, list[tuple[str, str]]] | None:
    """Lexical split into a base identifier and ("index"|"member"|"bit", text) steps."""
    base = re.match(identifier, expression)
    if base is None:
        return None
    steps: list[tuple[str, str]] = []
    rest = expression[base.end():]
    step = re.compile(rf"\[\s*([^\[\],]+?)\s*\]|\.({identifier})|\.([0-9]+)")
    position = 0
    while position < len(rest):
        match = step.match(rest, position)
        if match is None:
            return None
        if match.group(1) is not None:
            steps.append(("index", match.group(1)))
        elif match.group(2) is not None:
            steps.append(("member", match.group(2)))
        else:
            steps.append(("bit", match.group(3)))
        position = match.end()
    return (base.group(0), steps) if steps else None


def _from_declaration(
    data_type: str | None, datatype: Datatype | None, dimension: str | None, array_pattern: str,
) -> _Type | None:
    if not data_type:
        return None
    bounds = None
    name = data_type
    array = re.fullmatch(array_pattern, data_type, flags=re.IGNORECASE)
    if array:
        bounds = (int(array[1]), int(array[2]))
        name = array[3]
    elif dimension:
        span = re.fullmatch(r"(-?\d+)\.\.(-?\d+)", dimension)
        if span is None:
            return None
        bounds = (int(span[1]), int(span[2]))
    elif data_type.upper().startswith("ARRAY"):
        return None  # multi-dimensional or otherwise unparsed
    if bounds is not None and bounds[1] < bounds[0]:
        return None
    return _Type(name, bounds, datatype)


def resolve_member_path(
    expression: str, symbol: Any | None, *, identifier: str, array_pattern: str,
    datatypes: dict[str, Datatype], function_blocks: dict[str, dict[str, Any]],
    library_interfaces: dict[str, LibraryInterface],
) -> MemberPathResult:
    """Resolve ``expression`` given the already-looked-up base ``symbol``.

    ``symbol`` is a Tag or Function Block parameter (anything with ``data_type``
    and ``data_type_definition``), or None if the base is not a unique symbol.
    ``function_blocks`` maps a casefolded FB type name to its externally visible
    parameters keyed by casefolded name.
    """
    split = _split(expression, identifier)
    if split is None:
        return MemberPathResult("unresolved", detail="not an index/member/bit path")
    base, steps = split
    if symbol is None:
        return MemberPathResult("unresolved", detail=f"base {base!r} is not a unique declared symbol")
    current = _from_declaration(symbol.data_type, symbol.data_type_definition, None, array_pattern)
    if current is None:
        return MemberPathResult("unresolved", detail=f"base {base!r} has no proven type")
    lexical: list[str] = []
    for kind, text in steps:
        if current.datatype is None:
            current.datatype = datatypes.get(current.name.casefold())
        if kind == "index":
            if current.bounds is None:
                return MemberPathResult("unresolved", detail="index applied to a non-array")
            if not re.fullmatch(r"[0-9]+", text):
                return MemberPathResult("unresolved", detail=f"index {text!r} is not an integer literal")
            index = int(text)
            lower, upper = current.bounds
            if not lower <= index <= upper:
                return MemberPathResult(
                    "index_out_of_bounds", detail=f"index {index} outside declared bounds {lower}..{upper}")
            current = _Type(current.name, None, current.datatype)
            lexical.append(f"[{index}]")
            continue
        if current.bounds is not None:
            return MemberPathResult("unresolved", detail=f".{text} applied to an un-indexed array")
        if kind == "bit":
            width = BIT_WIDTHS.get(current.name.upper())
            if width is None:
                return MemberPathResult("unresolved", detail=f"bit select on non-integer type {current.name!r}")
            if int(text) >= width:
                return MemberPathResult(
                    "index_out_of_bounds", detail=f"bit {text} outside {current.name} width {width}")
            current = _Type("BOOL")
            lexical.append(f".{int(text)}")
            continue
        member = _member(current, text, function_blocks, library_interfaces, array_pattern)
        if member is None:
            return MemberPathResult("unresolved", detail=f"{current.name!r} has no proven member {text!r}")
        current, declared_name = member
        lexical.append(f".{declared_name}")  # declared spelling, not the source's case
    return MemberPathResult("resolved", MemberPath(base, tuple(lexical), current.name, current.bounds is not None))


def _member(
    current: _Type, name: str, function_blocks: dict[str, dict[str, Any]],
    library_interfaces: dict[str, LibraryInterface], array_pattern: str,
) -> tuple[_Type, str] | None:
    """The member's type and its declared name, or None if not uniquely proven."""
    key = name.casefold()
    if current.datatype is not None:
        matches = [m for m in current.datatype.members if m.name.casefold() == key]
        if len(matches) != 1:
            return None
        member = matches[0]
        found = _from_declaration(member.data_type_name, member.data_type, member.dimension, array_pattern)
        return (found, member.name) if found else None
    parameters = function_blocks.get(current.name.casefold())
    if parameters is not None:
        parameter = parameters.get(key)
        if parameter is None:
            return None
        found = _from_declaration(parameter.data_type, parameter.data_type_definition, None, array_pattern)
        return (found, parameter.name) if found else None
    interface = library_interfaces.get(current.name.casefold())
    if interface is not None:
        matches = [p for p in interface.parameters if (p.name or "").casefold() == key]
        if len(matches) != 1:
            return None
        found = _from_declaration(matches[0].data_type, None, None, array_pattern)
        return (found, matches[0].name or name) if found else None
    return None
