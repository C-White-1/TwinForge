"""Offline codec for one Logix Symbol Object enumeration page."""

from __future__ import annotations

from dataclasses import dataclass
from struct import pack, unpack_from

from .contracts import DiscoveryProviderError
from .controller import CipObjectEvidence
from .software_inventory_capture import (
    CipSoftwareInventoryItem,
    CipSoftwareInventoryPage,
)
from .software_inventory_plan import CipSoftwareInventoryCapability


LOGIX_SYMBOL_CLASS = 0x6B
GET_INSTANCE_ATTRIBUTE_LIST = 0x55
SUCCESS = 0x00
PARTIAL_TRANSFER = 0x06
BASE_ATTRIBUTES = (1, 2, 3, 5, 6, 8)
EXTERNAL_ACCESS_ATTRIBUTE = 10


@dataclass(frozen=True)
class LogixSymbolPageRequest:
    """One exact Symbol Object request controlled by the executor."""

    start_instance: int
    attributes: tuple[int, ...]
    request_data: bytes


@dataclass(frozen=True)
class LogixSymbolRecord:
    """One decoded symbol record with its original bytes retained."""

    instance_id: int
    name: str
    symbol_type: int
    symbol_address: int
    symbol_object_address: int
    software_control: int
    dimensions: tuple[int, int, int]
    external_access: int | None
    raw_hex: str


@dataclass(frozen=True)
class DecodedLogixSymbolPage:
    """All source records plus their allowed structural lowering."""

    page: CipSoftwareInventoryPage
    records: tuple[LogixSymbolRecord, ...]


def build_logix_symbol_page_request(
    start_instance: int,
    *,
    include_external_access: bool,
) -> LogixSymbolPageRequest:
    """Build the attribute-list payload for one starting instance."""
    if isinstance(start_instance, bool) or start_instance < 0:
        raise ValueError("start_instance must be a non-negative integer")
    attributes = BASE_ATTRIBUTES + (
        (EXTERNAL_ACCESS_ATTRIBUTE,) if include_external_access else ()
    )
    request_data = pack("<H", len(attributes)) + b"".join(
        pack("<H", attribute) for attribute in attributes
    )
    return LogixSymbolPageRequest(
        start_instance=start_instance,
        attributes=attributes,
        request_data=request_data,
    )


def decode_logix_symbol_page(
    payload: bytes,
    *,
    general_status: int,
    requested_capabilities: tuple[CipSoftwareInventoryCapability, ...],
    scope_program: str | None = None,
    include_external_access: bool,
    raw_reply: bytes | None = None,
    request_instance: int = 0,
) -> DecodedLogixSymbolPage:
    """Decode one successful or partial page without discarding source records."""
    if general_status not in {SUCCESS, PARTIAL_TRANSFER}:
        raise DiscoveryProviderError(
            "logix_symbol_page_failed",
            f"Symbol Object page returned CIP status {general_status}",
        )
    records = _decode_records(payload, include_external_access)
    if general_status == PARTIAL_TRANSFER and not records:
        raise DiscoveryProviderError(
            "logix_symbol_partial_without_cursor",
            "partial Symbol Object page contained no continuation instance",
        )
    allowed = set(requested_capabilities)
    items = tuple(
        item
        for record in records
        if (item := _lower_record(record, scope_program)) is not None
        and item.capability in allowed
    )
    next_cursor = (
        str(records[-1].instance_id + 1)
        if general_status == PARTIAL_TRANSFER
        else None
    )
    evidence = CipObjectEvidence(
        class_code=LOGIX_SYMBOL_CLASS,
        instance=request_instance,
        service=GET_INSTANCE_ATTRIBUTE_LIST,
        general_status=general_status,
        response_payload_hex=payload.hex(),
        raw_reply_hex=raw_reply.hex() if raw_reply is not None else None,
        decoded={"record_count": len(records)},
    )
    return DecodedLogixSymbolPage(
        page=CipSoftwareInventoryPage(
            items=items,
            next_cursor=next_cursor,
            object_evidence=(evidence,),
        ),
        records=records,
    )


def _decode_records(
    payload: bytes,
    include_external_access: bool,
) -> tuple[LogixSymbolRecord, ...]:
    records: list[LogixSymbolRecord] = []
    offset = 0
    try:
        while offset < len(payload):
            start = offset
            instance_id, offset = _uint32(payload, offset)
            name_length, offset = _uint16(payload, offset)
            end_name = offset + name_length
            if end_name > len(payload):
                raise ValueError("symbol name exceeds page payload")
            name = payload[offset:end_name].decode("utf-8")
            offset = end_name
            symbol_type, offset = _uint16(payload, offset)
            symbol_address, offset = _uint32(payload, offset)
            object_address, offset = _uint32(payload, offset)
            software_control, offset = _uint32(payload, offset)
            dim1, offset = _uint32(payload, offset)
            dim2, offset = _uint32(payload, offset)
            dim3, offset = _uint32(payload, offset)
            external_access = None
            if include_external_access:
                if offset >= len(payload):
                    raise ValueError("external access byte is missing")
                external_access = payload[offset]
                offset += 1
            records.append(
                LogixSymbolRecord(
                    instance_id=instance_id,
                    name=name,
                    symbol_type=symbol_type,
                    symbol_address=symbol_address,
                    symbol_object_address=object_address,
                    software_control=software_control,
                    dimensions=(dim1, dim2, dim3),
                    external_access=external_access,
                    raw_hex=payload[start:offset].hex(),
                )
            )
    except (UnicodeDecodeError, ValueError) as error:
        raise DiscoveryProviderError(
            "logix_symbol_page_malformed",
            f"could not decode Symbol Object page at offset {offset}: {error}",
        ) from error
    return tuple(records)


def _uint16(payload: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(payload):
        raise ValueError("UINT exceeds page payload")
    return unpack_from("<H", payload, offset)[0], offset + 2


def _uint32(payload: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(payload):
        raise ValueError("UDINT exceeds page payload")
    return unpack_from("<I", payload, offset)[0], offset + 4


def _lower_record(
    record: LogixSymbolRecord,
    scope_program: str | None,
) -> CipSoftwareInventoryItem | None:
    raw = {
        "symbol_type": record.symbol_type,
        "symbol_address": record.symbol_address,
        "symbol_object_address": record.symbol_object_address,
        "software_control": record.software_control,
        "dimensions": list(record.dimensions),
        "external_access": record.external_access,
        "raw_record_hex": record.raw_hex,
    }
    if record.name.startswith("Program:"):
        return CipSoftwareInventoryItem(
            CipSoftwareInventoryCapability.PROGRAMS,
            record.name.removeprefix("Program:"),
            instance_id=record.instance_id,
            raw_attributes=raw,
        )
    if record.name.startswith("Routine:"):
        return CipSoftwareInventoryItem(
            CipSoftwareInventoryCapability.ROUTINES,
            record.name.removeprefix("Routine:"),
            parent=scope_program,
            instance_id=record.instance_id,
            raw_attributes=raw,
        )
    if record.name.startswith("Task:"):
        return CipSoftwareInventoryItem(
            CipSoftwareInventoryCapability.TASKS,
            record.name.removeprefix("Task:"),
            instance_id=record.instance_id,
            raw_attributes=raw,
        )
    return CipSoftwareInventoryItem(
        CipSoftwareInventoryCapability.TAG_DEFINITIONS,
        record.name,
        parent=scope_program,
        instance_id=record.instance_id,
        raw_attributes=raw,
    )
