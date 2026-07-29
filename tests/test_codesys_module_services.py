from twinforge.exporters.codesys_module_services import (
    CODESYSModuleEquivalence,
    CODESYSModuleProfile,
    CODESYSModuleSupport,
    classify_codesys_module_service,
)
from twinforge.ir import IRControllerObjectIntent


def test_connection_state_is_normalized_not_raw_entry_status():
    capability = classify_codesys_module_service(
        IRControllerObjectIntent.CONNECTION_STATUS
    )

    assert capability.support is CODESYSModuleSupport.NORMALIZED
    assert "not the raw Rockwell EntryStatus" in capability.rationale


def test_runtime_inhibit_requires_bus_specific_support():
    capability = classify_codesys_module_service(
        IRControllerObjectIntent.SET_INHIBITED
    )

    assert capability.support is CODESYSModuleSupport.BUS_SPECIFIC
    assert "bus-driver support" in capability.rationale


def test_rockwell_mode_has_no_portable_codesys_equivalent():
    capability = classify_codesys_module_service(
        IRControllerObjectIntent.OPERATING_MODE
    )

    assert capability.support is CODESYSModuleSupport.UNAVAILABLE


def test_ethernet_ip_adapter_exposes_normalized_connection_state():
    capability = classify_codesys_module_service(
        IRControllerObjectIntent.CONNECTION_STATUS,
        CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER,
    )

    assert capability.support is CODESYSModuleSupport.NORMALIZED
    assert "RemoteAdapter_diag.GetDeviceState" in capability.adapter_api
    assert "not the raw Rockwell EntryStatus" in capability.rationale


def test_ethernet_ip_inhibit_requires_enable_and_reconfigure():
    capability = classify_codesys_module_service(
        IRControllerObjectIntent.SET_INHIBITED,
        CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER,
    )

    assert capability.support is CODESYSModuleSupport.NORMALIZED
    assert capability.adapter_api == (
        "RemoteAdapter_diag.Enable",
        "DED.CanReconfigure",
        "DED.Reconfigure",
    )
    assert "error handling" in capability.rationale


def test_ethernet_ip_faults_are_normalized_not_claimed_equivalent():
    fault_code = classify_codesys_module_service(
        IRControllerObjectIntent.FAULT_CODE,
        CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER,
    )
    fault_info = classify_codesys_module_service(
        IRControllerObjectIntent.FAULT_INFORMATION,
        CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER,
    )

    assert fault_code.support is CODESYSModuleSupport.NORMALIZED
    assert "rather than the Rockwell" in fault_code.rationale
    assert fault_info.support is CODESYSModuleSupport.NORMALIZED
    assert "RemoteAdapter_diag.sDiagString" in fault_info.adapter_api
    assert (
        fault_code.equivalence is CODESYSModuleEquivalence.APPROXIMATED
    )
    assert (
        fault_info.equivalence is CODESYSModuleEquivalence.APPROXIMATED
    )


def test_ethernet_ip_inhibit_remains_hardware_validation_dependent():
    capability = classify_codesys_module_service(
        IRControllerObjectIntent.SET_INHIBITED,
        CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER,
    )

    assert capability.support is CODESYSModuleSupport.NORMALIZED
    assert (
        capability.equivalence
        is CODESYSModuleEquivalence.HARDWARE_VALIDATION_REQUIRED
    )


def test_every_controller_intent_has_an_explicit_equivalence():
    capabilities = [
        classify_codesys_module_service(
            intent,
            CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER,
        )
        for intent in IRControllerObjectIntent
    ]

    assert len(capabilities) == len(IRControllerObjectIntent)
    assert all(
        isinstance(item.equivalence, CODESYSModuleEquivalence)
        for item in capabilities
    )
