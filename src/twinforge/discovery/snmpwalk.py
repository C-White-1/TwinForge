"""Decoder for common Net-SNMP ``snmpwalk`` text representations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .snmprec import (
    BRIDGE_FDB,
    BRIDGE_PORT_IF_INDEX,
    IF_NAME,
    IF_TABLE,
    IP_ADDRESS,
    LLDP_LOCAL_PORT_ID,
    LLDP_REMOTE,
    SnmprecValue,
)


@dataclass(frozen=True)
class SnmpwalkUnparsedLine:
    """One retained line that could not be represented canonically."""

    number: int
    text: str
    reason: str


@dataclass(frozen=True)
class SnmpwalkRecording:
    """Canonical records plus all non-empty evidence that was not decoded."""

    records: dict[str, SnmprecValue]
    unparsed_lines: tuple[SnmpwalkUnparsedLine, ...]


_SYMBOLIC_BASES = {
    "sysDescr": "1.3.6.1.2.1.1.1",
    "sysObjectID": "1.3.6.1.2.1.1.2",
    "sysUpTime": "1.3.6.1.2.1.1.3",
    "sysUpTimeInstance": "1.3.6.1.2.1.1.3.0",
    "sysContact": "1.3.6.1.2.1.1.4",
    "sysName": "1.3.6.1.2.1.1.5",
    "sysLocation": "1.3.6.1.2.1.1.6",
    "ifIndex": f"{IF_TABLE}.1",
    "ifDescr": f"{IF_TABLE}.2",
    "ifType": f"{IF_TABLE}.3",
    "ifSpeed": f"{IF_TABLE}.5",
    "ifPhysAddress": f"{IF_TABLE}.6",
    "ifAdminStatus": f"{IF_TABLE}.7",
    "ifOperStatus": f"{IF_TABLE}.8",
    "ifName": IF_NAME,
    "ipAdEntAddr": f"{IP_ADDRESS}.1",
    "ipAdEntIfIndex": f"{IP_ADDRESS}.2",
    "ipAdEntNetMask": f"{IP_ADDRESS}.3",
    "dot1dBasePortIfIndex": BRIDGE_PORT_IF_INDEX,
    "dot1dTpFdbAddress": f"{BRIDGE_FDB}.1",
    "dot1dTpFdbPort": f"{BRIDGE_FDB}.2",
    "dot1dTpFdbStatus": f"{BRIDGE_FDB}.3",
    "lldpLocPortId": LLDP_LOCAL_PORT_ID,
    "lldpRemChassisId": f"{LLDP_REMOTE}.5",
    "lldpRemPortId": f"{LLDP_REMOTE}.7",
    "lldpRemSysName": f"{LLDP_REMOTE}.9",
}

_INTEGER_TYPES = {
    "INTEGER": "2",
    "INTEGER32": "2",
    "COUNTER": "65",
    "COUNTER32": "65",
    "GAUGE": "66",
    "GAUGE32": "66",
    "UNSIGNED32": "66",
    "TIMETICKS": "67",
    "COUNTER64": "70",
}
_STRING_TYPES = {
    "STRING": "4",
    "OCTET STRING": "4",
    "HEX-STRING": "4",
    "IPADDRESS": "64",
    "OID": "6",
    "OBJECT IDENTIFIER": "6",
}


def _numeric_oid(value: str) -> str | None:
    candidate = value.strip().lstrip(".")
    if candidate.startswith("iso."):
        candidate = f"1.{candidate[4:]}"
    if candidate and all(part.isdigit() for part in candidate.split(".")):
        return candidate
    symbol = candidate.rsplit("::", maxsplit=1)[-1]
    match = re.fullmatch(r"([A-Za-z][A-Za-z0-9-]*)(?:\.(.+))?", symbol)
    if match is None:
        return None
    base = _SYMBOLIC_BASES.get(match.group(1))
    suffix = match.group(2)
    if base is None:
        return None
    if suffix is None:
        return base if match.group(1) == "sysUpTimeInstance" else None
    if not all(part.isdigit() for part in suffix.split(".")):
        return None
    return f"{base}.{suffix}"


def _integer_value(value: str) -> int | None:
    ticks = re.match(r"\((\d+)\)", value)
    if ticks:
        return int(ticks.group(1))
    enum = re.fullmatch(r".*\((-?\d+)\)", value.strip())
    if enum:
        return int(enum.group(1))
    plain = re.match(r"-?\d+", value.strip())
    return int(plain.group(0)) if plain else None


def _decode_value(type_name: str, raw_value: str) -> SnmprecValue | None:
    normalized = type_name.strip().upper()
    if normalized in _INTEGER_TYPES:
        value = _integer_value(raw_value)
        if value is None:
            return None
        return SnmprecValue(_INTEGER_TYPES[normalized], value)
    if normalized in _STRING_TYPES:
        value = raw_value.strip()
        if normalized == "HEX-STRING":
            value = "".join(value.split()).lower()
        return SnmprecValue(_STRING_TYPES[normalized], value)
    return None


def read_snmpwalk(path: str | Path) -> SnmpwalkRecording:
    """Read common Net-SNMP output while retaining all undecoded lines."""
    records: dict[str, SnmprecValue] = {}
    unparsed: list[SnmpwalkUnparsedLine] = []
    for number, text in enumerate(
        Path(path).read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        line = text.strip()
        if not line:
            continue
        assignment = re.match(r"^(.+?)\s*=\s*([^:]+):\s*(.*)$", line)
        if assignment is None:
            unparsed.append(SnmpwalkUnparsedLine(number, text, "syntax"))
            continue
        oid = _numeric_oid(assignment.group(1))
        if oid is None:
            unparsed.append(SnmpwalkUnparsedLine(number, text, "oid"))
            continue
        value = _decode_value(assignment.group(2), assignment.group(3))
        if value is None:
            unparsed.append(SnmpwalkUnparsedLine(number, text, "type_or_value"))
            continue
        records[oid] = value
    return SnmpwalkRecording(records, tuple(unparsed))
