"""CODESYS support classification for neutral module-service intents.

The generic IEC exporter preserves controller-object operations. This module
describes what a future CODESYS adapter may safely promise; it deliberately
does not invent a universal device-tree API where support is supplied by
individual bus drivers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from twinforge.ir import IRControllerObjectIntent


class CODESYSModuleSupport(str, Enum):
    """Strength of a CODESYS mapping for one neutral service."""

    NORMALIZED = "normalized"
    BUS_SPECIFIC = "bus_specific"
    UNAVAILABLE = "unavailable"


class CODESYSModuleEquivalence(str, Enum):
    """Semantic relationship to the captured Rockwell module service."""

    APPROXIMATED = "approximated"
    UNAVAILABLE = "unavailable"
    HARDWARE_VALIDATION_REQUIRED = "hardware_validation_required"


class CODESYSModuleProfile(str, Enum):
    """Established CODESYS device-service profile."""

    GENERIC = "generic"
    ETHERNET_IP_REMOTE_ADAPTER = "ethernet_ip_remote_adapter"


@dataclass(frozen=True)
class CODESYSModuleCapability:
    """Evidence-based CODESYS support classification."""

    support: CODESYSModuleSupport
    rationale: str
    adapter_api: tuple[str, ...] = ()
    equivalence: CODESYSModuleEquivalence = (
        CODESYSModuleEquivalence.UNAVAILABLE
    )


_CAPABILITIES = {
    IRControllerObjectIntent.INSTANCE_IDENTITY: CODESYSModuleCapability(
        CODESYSModuleSupport.BUS_SPECIFIC,
        "device identity and IEC objects depend on the configured bus driver",
        equivalence=CODESYSModuleEquivalence.UNAVAILABLE,
    ),
    IRControllerObjectIntent.CONNECTION_STATUS: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "CAA Device Diagnosis exposes a portable running/not-running state, "
        "but not the raw Rockwell EntryStatus word",
        equivalence=CODESYSModuleEquivalence.APPROXIMATED,
    ),
    IRControllerObjectIntent.FAULT_CODE: CODESYSModuleCapability(
        CODESYSModuleSupport.BUS_SPECIFIC,
        "fault codes are exposed by device- or bus-specific diagnostics",
        equivalence=CODESYSModuleEquivalence.UNAVAILABLE,
    ),
    IRControllerObjectIntent.FAULT_INFORMATION: CODESYSModuleCapability(
        CODESYSModuleSupport.BUS_SPECIFIC,
        "diagnostic detail is exposed by device- or bus-specific diagnostics",
        equivalence=CODESYSModuleEquivalence.UNAVAILABLE,
    ),
    IRControllerObjectIntent.OPERATING_MODE: CODESYSModuleCapability(
        CODESYSModuleSupport.UNAVAILABLE,
        "no portable CODESYS equivalent of the Rockwell Module Mode value",
        equivalence=CODESYSModuleEquivalence.UNAVAILABLE,
    ),
    IRControllerObjectIntent.SET_INHIBITED: CODESYSModuleCapability(
        CODESYSModuleSupport.BUS_SPECIFIC,
        "runtime enable/disable requires explicit bus-driver support",
        equivalence=CODESYSModuleEquivalence.UNAVAILABLE,
    ),
    IRControllerObjectIntent.SOURCE_SPECIFIC: CODESYSModuleCapability(
        CODESYSModuleSupport.UNAVAILABLE,
        "the source-specific service has no established neutral mapping",
        equivalence=CODESYSModuleEquivalence.UNAVAILABLE,
    ),
}

_ETHERNET_IP_CAPABILITIES = {
    IRControllerObjectIntent.INSTANCE_IDENTITY: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "the generated remote-adapter device exposes CAA Device Diagnosis "
        "identity, not a Logix module instance number",
        ("RemoteAdapter_diag.GetDeviceInfo",),
        CODESYSModuleEquivalence.APPROXIMATED,
    ),
    IRControllerObjectIntent.CONNECTION_STATUS: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "AdapterState and DED.DEVICE_STATE expose connection health, but not "
        "the raw Rockwell EntryStatus word",
        ("RemoteAdapter_diag.eState", "RemoteAdapter_diag.GetDeviceState"),
        CODESYSModuleEquivalence.APPROXIMATED,
    ),
    IRControllerObjectIntent.FAULT_CODE: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "CAA Device Diagnosis exposes structured device errors rather than "
        "the Rockwell Module FaultCode value",
        ("DED.GetDeviceError", "RemoteAdapter_diag.GetDeviceState"),
        CODESYSModuleEquivalence.APPROXIMATED,
    ),
    IRControllerObjectIntent.FAULT_INFORMATION: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "the remote adapter exposes diagnostic availability and text rather "
        "than the Rockwell Module FaultInfo value",
        (
            "RemoteAdapter_diag.xDiagnosticAvailable",
            "RemoteAdapter_diag.sDiagString",
        ),
        CODESYSModuleEquivalence.APPROXIMATED,
    ),
    IRControllerObjectIntent.OPERATING_MODE: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "device state and Enable represent target operation, but do not "
        "reproduce the numeric Rockwell Module Mode attribute",
        ("RemoteAdapter_diag.Enable", "RemoteAdapter_diag.GetDeviceState"),
        CODESYSModuleEquivalence.APPROXIMATED,
    ),
    IRControllerObjectIntent.SET_INHIBITED: CODESYSModuleCapability(
        CODESYSModuleSupport.NORMALIZED,
        "the EtherNet/IP diagnostic remote adapter implements "
        "IReconfigureProvider; changing Enable requires an explicit "
        "reconfigure operation and error handling",
        (
            "RemoteAdapter_diag.Enable",
            "DED.CanReconfigure",
            "DED.Reconfigure",
        ),
        CODESYSModuleEquivalence.HARDWARE_VALIDATION_REQUIRED,
    ),
    IRControllerObjectIntent.SOURCE_SPECIFIC: _CAPABILITIES[
        IRControllerObjectIntent.SOURCE_SPECIFIC
    ],
}


def classify_codesys_module_service(
    intent: IRControllerObjectIntent,
    profile: CODESYSModuleProfile = CODESYSModuleProfile.GENERIC,
) -> CODESYSModuleCapability:
    """Return the established support level for a CODESYS target."""

    if profile is CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER:
        return _ETHERNET_IP_CAPABILITIES[intent]
    return _CAPABILITIES[intent]
