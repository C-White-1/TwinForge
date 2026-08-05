"""Offline SNMPSim recording adapter for discovery development and tests."""

from __future__ import annotations

import bz2
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contracts import (
    DiscoveryProviderError,
    DiscoveryTarget,
    SnmpForwardingEntryObservation,
    SnmpInterfaceObservation,
    SnmpNeighbourObservation,
    SnmpNetworkAddressObservation,
    SnmpNodeObservation,
    SnmpPhysicalEntityObservation,
)

SYSTEM_OIDS = {
    "1.3.6.1.2.1.1.1.0": "system_description",
    "1.3.6.1.2.1.1.2.0": "system_object_id",
    "1.3.6.1.2.1.1.3.0": "uptime_ticks",
    "1.3.6.1.2.1.1.4.0": "system_contact",
    "1.3.6.1.2.1.1.5.0": "system_name",
    "1.3.6.1.2.1.1.6.0": "system_location",
}
IF_TABLE = "1.3.6.1.2.1.2.2.1"
IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
IP_ADDRESS = "1.3.6.1.2.1.4.20.1"
BRIDGE_PORT_IF_INDEX = "1.3.6.1.2.1.17.1.4.1.2"
BRIDGE_FDB = "1.3.6.1.2.1.17.4.3.1"
LLDP_LOCAL_PORT_ID = "1.0.8802.1.1.2.1.3.7.1.3"
LLDP_REMOTE = "1.0.8802.1.1.2.1.4.1.1"
ENT_PHYSICAL_ENTRY = "1.3.6.1.2.1.47.1.1.1.1"


@dataclass(frozen=True)
class SnmprecValue:
    """One decoded value from a native SNMPSim recording."""

    type_code: str
    value: str | int


class SnmprecSizeLimitError(ValueError):
    """Raised before parsing when decompressed evidence exceeds its budget."""


@dataclass(frozen=True)
class SnmprecUnparsedLine:
    """One physical SNMPREC line retained after tolerant decoding failed."""

    number: int
    text: str
    reason: str


@dataclass(frozen=True)
class SnmprecRecording:
    """Canonical records plus malformed physical lines retained as evidence."""

    records: dict[str, SnmprecValue]
    unparsed_lines: tuple[SnmprecUnparsedLine, ...]


def read_snmprec_recording(
    path: str | Path,
    *,
    max_bytes: int | None = None,
) -> SnmprecRecording:
    """Decode intact records while retaining malformed physical lines."""
    records: dict[str, SnmprecValue] = {}
    unparsed: list[SnmprecUnparsedLine] = []
    source = Path(path)
    if source.name.lower().endswith(".bz2"):
        with bz2.open(source, mode="rb") as stream:
            payload = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
    else:
        payload = source.read_bytes()
    if max_bytes is not None and len(payload) > max_bytes:
        raise SnmprecSizeLimitError(
            f"decompressed recording exceeds {max_bytes} bytes"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        # SNMP OCTET STRING evidence in older recordings may contain arbitrary
        # bytes. Latin-1 preserves every byte one-to-one instead of discarding
        # or replacing evidence.
        text = payload.decode("latin-1")
    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if not line or line.startswith("#"):
            continue
        fields = line.split("|", maxsplit=2)
        if len(fields) != 3:
            unparsed.append(SnmprecUnparsedLine(number, line, "syntax"))
            continue
        oid, type_code, raw_value = fields
        value: str | int = raw_value
        if type_code in {"2", "65", "66", "67", "70"}:
            try:
                value = int(raw_value)
            except ValueError:
                unparsed.append(
                    SnmprecUnparsedLine(number, line, "integer_value")
                )
                continue
        records[oid] = SnmprecValue(type_code=type_code, value=value)
    return SnmprecRecording(records, tuple(unparsed))


def read_snmprec(
    path: str | Path,
    *,
    max_bytes: int | None = None,
) -> dict[str, SnmprecValue]:
    """Strictly read a recording, rejecting any malformed physical line."""
    recording = read_snmprec_recording(path, max_bytes=max_bytes)
    if recording.unparsed_lines:
        first = recording.unparsed_lines[0]
        raise ValueError(f"invalid SNMPSim record at line {first.number}")
    return recording.records


def _string(records: dict[str, SnmprecValue], oid: str) -> str | None:
    record = records.get(oid)
    return None if record is None else str(record.value)


def _integer(records: dict[str, SnmprecValue], oid: str) -> int | None:
    record = records.get(oid)
    return record.value if record is not None and isinstance(record.value, int) else None


def _mac(value: str | None) -> str | None:
    if value is None or len(value) % 2:
        return value
    return ":".join(value[index : index + 2] for index in range(0, len(value), 2))


def _suffix(oid: str, prefix: str) -> str | None:
    marker = f"{prefix}."
    return oid[len(marker) :] if oid.startswith(marker) else None


def _raw(
    records: dict[str, SnmprecValue],
) -> dict[str, str | int | bool | None]:
    return {oid: record.value for oid, record in sorted(records.items())}


def _interfaces(
    records: dict[str, SnmprecValue],
) -> tuple[SnmpInterfaceObservation, ...]:
    indexes = sorted(
        record.value
        for oid, record in records.items()
        if _suffix(oid, f"{IF_TABLE}.1") is not None
        and isinstance(record.value, int)
    )
    addresses: dict[int, list[SnmpNetworkAddressObservation]] = {}
    raw_by_index: dict[int, dict[str, str | int | bool | None]] = {}
    for oid in records:
        if oid.startswith(f"{IF_TABLE}."):
            try:
                raw_index = int(oid.rsplit(".", maxsplit=1)[-1])
            except ValueError:
                pass
            else:
                raw_by_index.setdefault(raw_index, {})[oid] = records[oid].value
        address = _suffix(oid, f"{IP_ADDRESS}.1")
        if address is None:
            continue
        interface_index = _integer(records, f"{IP_ADDRESS}.2.{address}")
        netmask = _string(records, f"{IP_ADDRESS}.3.{address}")
        if interface_index is None:
            continue
        prefix = _netmask_prefix(netmask)
        addresses.setdefault(interface_index, []).append(
            SnmpNetworkAddressObservation(address, prefix)
        )

    return tuple(
        SnmpInterfaceObservation(
            index=index,
            name=_string(records, f"{IF_NAME}.{index}"),
            description=_string(records, f"{IF_TABLE}.2.{index}"),
            interface_type=_integer(records, f"{IF_TABLE}.3.{index}"),
            mac_address=_mac(_string(records, f"{IF_TABLE}.6.{index}")),
            speed_bps=_integer(records, f"{IF_TABLE}.5.{index}"),
            admin_status=_integer(records, f"{IF_TABLE}.7.{index}"),
            operational_status=_integer(records, f"{IF_TABLE}.8.{index}"),
            addresses=tuple(addresses.get(index, ())),
            raw_oids=raw_by_index.get(index, {}),
        )
        for index in indexes
    )


def _netmask_prefix(netmask: str | None) -> int | None:
    if netmask is None:
        return None
    try:
        octets = [int(item) for item in netmask.split(".")]
    except ValueError:
        return None
    if len(octets) != 4 or any(item < 0 or item > 255 for item in octets):
        return None
    bits = "".join(f"{item:08b}" for item in octets)
    if "01" in bits:
        return None
    return bits.count("1")


def _forwarding_entries(
    records: dict[str, SnmprecValue],
) -> tuple[SnmpForwardingEntryObservation, ...]:
    bridge_to_interface = {
        int(port): record.value
        for oid, record in records.items()
        if (port := _suffix(oid, BRIDGE_PORT_IF_INDEX)) is not None
        and isinstance(record.value, int)
    }
    entries: list[SnmpForwardingEntryObservation] = []
    for oid, record in records.items():
        suffix = _suffix(oid, f"{BRIDGE_FDB}.1")
        if suffix is None:
            continue
        bridge_port = _integer(records, f"{BRIDGE_FDB}.2.{suffix}")
        if bridge_port is None:
            continue
        octets = suffix.split(".")
        mac_address = ":".join(f"{int(item):02x}" for item in octets)
        entries.append(
            SnmpForwardingEntryObservation(
                mac_address=mac_address,
                bridge_port=bridge_port,
                interface_index=bridge_to_interface.get(bridge_port),
                status=_integer(records, f"{BRIDGE_FDB}.3.{suffix}"),
                raw_oids={oid: record.value},
            )
        )
    return tuple(entries)


def _neighbours(
    records: dict[str, SnmprecValue],
    interfaces: tuple[SnmpInterfaceObservation, ...],
) -> tuple[SnmpNeighbourObservation, ...]:
    name_to_index = {
        interface.name: interface.index
        for interface in interfaces
        if interface.name is not None
    }
    local_port_ids = {
        int(port): record.value
        for oid, record in records.items()
        if (port := _suffix(oid, LLDP_LOCAL_PORT_ID)) is not None
    }
    neighbours: list[SnmpNeighbourObservation] = []
    for oid, record in records.items():
        suffix = _suffix(oid, f"{LLDP_REMOTE}.5")
        if suffix is None:
            continue
        index = suffix.split(".")
        if len(index) < 3:
            continue
        local_port = int(index[-2])
        local_port_id = local_port_ids.get(local_port)
        raw_chassis = str(record.value)
        neighbours.append(
            SnmpNeighbourObservation(
                protocol="lldp",
                local_port_number=local_port,
                local_interface_index=name_to_index.get(str(local_port_id)),
                remote_chassis_id=_mac(raw_chassis) or raw_chassis,
                remote_port_id=_string(records, f"{LLDP_REMOTE}.7.{suffix}") or "",
                remote_system_name=_string(records, f"{LLDP_REMOTE}.9.{suffix}"),
                raw_oids={oid: record.value},
            )
        )
    return tuple(neighbours)


def _physical_entities(
    records: dict[str, SnmprecValue],
) -> tuple[SnmpPhysicalEntityObservation, ...]:
    raw_by_index: dict[int, dict[str, str | int | bool | None]] = {}
    indexes: set[int] = set()
    for oid, record in records.items():
        suffix = _suffix(oid, ENT_PHYSICAL_ENTRY)
        if suffix is None:
            continue
        parts = suffix.split(".")
        if len(parts) != 2:
            continue
        try:
            index = int(parts[1])
        except ValueError:
            continue
        indexes.add(index)
        raw_by_index.setdefault(index, {})[oid] = record.value

    def text(column: int, index: int) -> str | None:
        return _string(records, f"{ENT_PHYSICAL_ENTRY}.{column}.{index}")

    def integer(column: int, index: int) -> int | None:
        return _integer(records, f"{ENT_PHYSICAL_ENTRY}.{column}.{index}")

    entities: list[SnmpPhysicalEntityObservation] = []
    for index in sorted(indexes):
        truth_value = integer(16, index)
        uri_text = text(18, index)
        entities.append(
            SnmpPhysicalEntityObservation(
                index=index,
                description=text(2, index),
                vendor_type_oid=text(3, index),
                contained_in=integer(4, index),
                physical_class=integer(5, index),
                parent_relative_position=integer(6, index),
                name=text(7, index),
                hardware_revision=text(8, index),
                firmware_revision=text(9, index),
                software_revision=text(10, index),
                serial_number=text(11, index),
                manufacturer_name=text(12, index),
                model_name=text(13, index),
                alias=text(14, index),
                asset_id=text(15, index),
                is_fru=(
                    True
                    if truth_value == 1
                    else False if truth_value == 2 else None
                ),
                manufacturing_date=text(17, index),
                uris=tuple(uri_text.split()) if uri_text else (),
                uuid=text(19, index),
                raw_oids=raw_by_index[index],
            )
        )
    return tuple(entities)


def build_snmp_node(
    target: DiscoveryTarget,
    captured_at: datetime,
    records: dict[str, SnmprecValue],
) -> SnmpNodeObservation:
    """Build observation records from static SNMP varbind evidence."""
    interfaces = _interfaces(records)
    return SnmpNodeObservation(
        target=target,
        captured_at=captured_at,
        system_name=_string(records, "1.3.6.1.2.1.1.5.0"),
        system_description=_string(records, "1.3.6.1.2.1.1.1.0"),
        system_object_id=_string(records, "1.3.6.1.2.1.1.2.0"),
        system_contact=_string(records, "1.3.6.1.2.1.1.4.0"),
        system_location=_string(records, "1.3.6.1.2.1.1.6.0"),
        uptime_ticks=_integer(records, "1.3.6.1.2.1.1.3.0"),
        interfaces=interfaces,
        neighbours=_neighbours(records, interfaces),
        forwarding_entries=_forwarding_entries(records),
        physical_entities=_physical_entities(records),
        raw_oids=_raw(records),
    )


class SnmprecDiscoveryProvider:
    """Supply SNMP observations from explicit local recording files."""

    def __init__(self, recordings: dict[str, str | Path]) -> None:
        self._recordings = {key: Path(path) for key, path in recordings.items()}

    def read_snmp_node(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> SnmpNodeObservation:
        """Read and lower the recording associated with ``target.key``."""
        try:
            path = self._recordings[target.key]
        except KeyError as error:
            raise DiscoveryProviderError(
                "snmprec_mapping_missing",
                f"no SNMPSim recording is mapped to {target.key}",
            ) from error
        try:
            records = read_snmprec(path)
        except (OSError, ValueError) as error:
            raise DiscoveryProviderError(
                "snmprec_read_failed",
                f"could not read SNMPSim recording for {target.key}: {error}",
            ) from error
        return build_snmp_node(target, captured_at, records)
