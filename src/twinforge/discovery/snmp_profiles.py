"""Explicit opt-in SNMP observation profiles beyond baseline discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SnmpObservationProfileStatus(str, Enum):
    """Implementation status of an optional SNMP observation profile."""

    EVIDENCE_ONLY = "evidence_only"
    LOWERED = "lowered"


@dataclass(frozen=True)
class SnmpObservationProfile:
    """Bounded OID roots and semantics for an explicit capture purpose."""

    key: str
    name: str
    oid_roots: tuple[str, ...]
    enabled_by_default: bool
    status: SnmpObservationProfileStatus
    semantics: str
    limitations: tuple[str, ...]


RMON_ETHERNET_STATISTICS_PROFILE = SnmpObservationProfile(
    key="rmon-ethernet-statistics",
    name="RMON Ethernet statistics",
    oid_roots=("1.3.6.1.2.1.16.1.1",),
    enabled_by_default=False,
    status=SnmpObservationProfileStatus.EVIDENCE_ONLY,
    semantics="time-varying Ethernet probe counters",
    limitations=(
        "the RFC 2819 statistics group is optional",
        "rows exist only for interfaces monitored by the agent",
        "counter interpretation requires capture time and continuity evidence",
        "TwinForge never creates or modifies RMON control rows",
    ),
)


def optional_snmp_observation_profiles() -> tuple[SnmpObservationProfile, ...]:
    """Return optional profiles in deterministic key order."""
    return (RMON_ETHERNET_STATISTICS_PROFILE,)
