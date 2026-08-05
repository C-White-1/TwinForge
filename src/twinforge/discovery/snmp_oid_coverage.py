"""Specification-oriented classification of observed numeric SNMP OIDs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SnmpOidFamily:
    """Stable family classification without requiring local MIB modules."""

    key: str
    standard: bool
    lowered: bool


_STANDARD_FAMILIES: tuple[tuple[str, str, bool], ...] = (
    ("1.0.8802.1.1.2", "ieee-lldp", True),
    ("1.3.6.1.2.1.1", "mib-2.system", True),
    ("1.3.6.1.2.1.2", "mib-2.interfaces", True),
    ("1.3.6.1.2.1.4", "mib-2.ip", True),
    ("1.3.6.1.2.1.5", "mib-2.icmp", False),
    ("1.3.6.1.2.1.6", "mib-2.tcp", False),
    ("1.3.6.1.2.1.7", "mib-2.udp", False),
    ("1.3.6.1.2.1.11", "mib-2.snmp", False),
    ("1.3.6.1.2.1.14", "ospf-mib", False),
    ("1.3.6.1.2.1.16", "rmon-mib", False),
    ("1.3.6.1.2.1.17", "mib-2.bridge", True),
    ("1.3.6.1.2.1.25", "host-resources", False),
    ("1.3.6.1.2.1.31", "if-mib", True),
    # ENTITY-MIB version 4 is specified by RFC 6933 (mib-2.47).
    ("1.3.6.1.2.1.47", "entity-mib", True),
    ("1.3.6.1.2.1.55", "ipv6-mib-historic", False),
)


def classify_snmp_oid(oid: str) -> SnmpOidFamily:
    """Classify one numeric OID by its most specific recognized subtree."""
    normalized = oid.strip().lstrip(".")
    for prefix, key, lowered in _STANDARD_FAMILIES:
        if normalized == prefix or normalized.startswith(f"{prefix}."):
            return SnmpOidFamily(key=key, standard=True, lowered=lowered)
    enterprise_prefix = "1.3.6.1.4.1."
    if normalized.startswith(enterprise_prefix):
        suffix = normalized[len(enterprise_prefix) :]
        number = suffix.split(".", maxsplit=1)[0]
        if number.isdigit():
            return SnmpOidFamily(
                key=f"enterprise.{number}",
                standard=False,
                lowered=False,
            )
    mib2_prefix = "1.3.6.1.2.1."
    if normalized.startswith(mib2_prefix):
        branch = normalized[len(mib2_prefix) :].split(".", maxsplit=1)[0]
        return SnmpOidFamily(
            key=f"mib-2.{branch}",
            standard=True,
            lowered=False,
        )
    return SnmpOidFamily(key="other", standard=False, lowered=False)


def count_snmp_oid_families(oids: Iterable[str]) -> dict[str, int]:
    """Count OIDs by stable family key in deterministic key order."""
    counts = Counter(classify_snmp_oid(oid).key for oid in oids)
    return dict(sorted(counts.items()))


def lowered_snmp_oid_families() -> tuple[str, ...]:
    """Return families with current semantic lowering support."""
    return tuple(
        key for _, key, lowered in _STANDARD_FAMILIES if lowered
    )
