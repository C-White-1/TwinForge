from struct import pack

import pytest

from twinforge.discovery.contracts import DiscoveryProviderError
from twinforge.discovery.logix_symbol_codec import (
    BASE_ATTRIBUTES,
    EXTERNAL_ACCESS_ATTRIBUTE,
    GET_INSTANCE_ATTRIBUTE_LIST,
    LOGIX_SYMBOL_CLASS,
    build_logix_symbol_page_request,
    decode_logix_symbol_page,
)
from twinforge.discovery.software_inventory_plan import (
    CipSoftwareInventoryCapability,
)


def _record(instance: int, name: str, *, external_access: int = 2) -> bytes:
    encoded_name = name.encode("utf-8")
    return b"".join(
        (
            pack("<I", instance),
            pack("<H", len(encoded_name)),
            encoded_name,
            pack("<H", 0x00C1),
            pack("<I", 100 + instance),
            pack("<I", 200 + instance),
            pack("<I", 0),
            pack("<III", 0, 0, 0),
            bytes((external_access,)),
        )
    )


def test_request_encodes_exact_symbol_attribute_allowlist() -> None:
    request = build_logix_symbol_page_request(
        17,
        include_external_access=True,
    )

    assert LOGIX_SYMBOL_CLASS == 0x6B
    assert GET_INSTANCE_ATTRIBUTE_LIST == 0x55
    assert request.start_instance == 17
    assert request.attributes == BASE_ATTRIBUTES + (EXTERNAL_ACCESS_ATTRIBUTE,)
    assert request.request_data == bytes.fromhex(
        "07000100020003000500060008000a00"
    )


def test_partial_page_preserves_records_and_returns_next_instance() -> None:
    capabilities = (
        CipSoftwareInventoryCapability.PROGRAMS,
        CipSoftwareInventoryCapability.TAG_DEFINITIONS,
        CipSoftwareInventoryCapability.TASKS,
    )
    payload = b"".join(
        (
            _record(4, "Program:MainProgram"),
            _record(8, "Task:MainTask"),
            _record(12, "MotorRun"),
        )
    )

    decoded = decode_logix_symbol_page(
        payload,
        general_status=0x06,
        requested_capabilities=capabilities,
        include_external_access=True,
        raw_reply=b"raw-packet",
    )

    assert decoded.page.next_cursor == "13"
    assert [item.name for item in decoded.page.items] == [
        "MainProgram",
        "MainTask",
        "MotorRun",
    ]
    assert len(decoded.records) == 3
    assert decoded.records[2].raw_hex == _record(12, "MotorRun").hex()
    evidence = decoded.page.object_evidence[0]
    assert evidence.response_payload_hex == payload.hex()
    assert evidence.raw_reply_hex == b"raw-packet".hex()


def test_program_scope_lowers_routine_and_tag_parentage() -> None:
    decoded = decode_logix_symbol_page(
        _record(2, "Routine:MainRoutine") + _record(3, "ProgramState"),
        general_status=0,
        requested_capabilities=(
            CipSoftwareInventoryCapability.ROUTINES,
            CipSoftwareInventoryCapability.TAG_DEFINITIONS,
        ),
        scope_program="MainProgram",
        include_external_access=True,
    )

    assert [(item.name, item.parent) for item in decoded.page.items] == [
        ("MainRoutine", "MainProgram"),
        ("ProgramState", "MainProgram"),
    ]
    assert decoded.page.next_cursor is None


def test_codec_rejects_failed_malformed_and_cursorless_partial_pages() -> None:
    with pytest.raises(DiscoveryProviderError, match="CIP status 5"):
        decode_logix_symbol_page(
            b"",
            general_status=5,
            requested_capabilities=(),
            include_external_access=True,
        )
    with pytest.raises(DiscoveryProviderError, match="external access byte"):
        decode_logix_symbol_page(
            _record(1, "Broken")[:-1],
            general_status=0,
            requested_capabilities=(),
            include_external_access=True,
        )
    with pytest.raises(DiscoveryProviderError, match="no continuation"):
        decode_logix_symbol_page(
            b"",
            general_status=6,
            requested_capabilities=(),
            include_external_access=True,
        )
