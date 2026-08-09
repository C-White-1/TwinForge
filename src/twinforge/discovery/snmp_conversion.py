"""Controlled offline conversion of explicitly declared SNMP walk evidence."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .snmpwalk import read_snmpwalk


class SnmpConversionError(ValueError):
    """A conversion plan or input violates the lossless workflow policy."""


@dataclass(frozen=True)
class SnmpWalkConversionPlan:
    """Attributable declaration that one unusual file is Net-SNMP walk text."""

    input_path: Path
    output_path: Path
    expected_sha256: str
    source_url: str
    license: str
    device_category: str
    sanitized: bool
    approved_by: str
    approved_at: datetime
    rationale: str
    max_input_bytes: int = 16 * 1024 * 1024
    allow_unparsed_lines: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "source_url",
            "license",
            "device_category",
            "approved_by",
            "rationale",
        ):
            value = getattr(self, field_name)
            if not value or value != value.strip():
                raise SnmpConversionError(f"{field_name} must be non-empty and trimmed")
        checksum = self.expected_sha256.lower()
        if len(checksum) != 64 or any(
            character not in "0123456789abcdef" for character in checksum
        ):
            raise SnmpConversionError("expected_sha256 must contain 64 hexadecimal characters")
        if self.approved_at.tzinfo is None:
            raise SnmpConversionError("approved_at must include a timezone")
        if self.max_input_bytes < 1:
            raise SnmpConversionError("max_input_bytes must be positive")
        if self.output_path.suffix.casefold() != ".snmprec":
            raise SnmpConversionError("output_path must use the .snmprec extension")
        if self.input_path.resolve() == self.output_path.resolve():
            raise SnmpConversionError("input and output paths must differ")


@dataclass(frozen=True)
class SnmpConversionReceipt:
    """Checksummed provenance for one completed offline conversion."""

    input_path: str
    output_path: str
    input_format: str
    output_format: str
    input_sha256: str
    output_sha256: str
    record_count: int
    unparsed_line_count: int
    unparsed_sidecar_path: str
    source_url: str
    license: str
    device_category: str
    sanitized: bool
    approved_by: str
    approved_at: str
    rationale: str
    network_access: bool = False


def snmp_walk_conversion_plan_data(plan: SnmpWalkConversionPlan) -> dict[str, object]:
    """Return a deterministic dry-run representation without reading input."""
    return {
        "operation": "convert_net_snmp_walk",
        "dry_run": True,
        "input_path": str(plan.input_path),
        "output_path": str(plan.output_path),
        "expected_sha256": plan.expected_sha256.lower(),
        "source_url": plan.source_url,
        "license": plan.license,
        "device_category": plan.device_category,
        "sanitized": plan.sanitized,
        "approved_by": plan.approved_by,
        "approved_at": plan.approved_at.isoformat(),
        "rationale": plan.rationale,
        "max_input_bytes": plan.max_input_bytes,
        "allow_unparsed_lines": plan.allow_unparsed_lines,
        "network_access": False,
        "overwrite": False,
    }


def snmp_walk_conversion_plan_json(plan: SnmpWalkConversionPlan) -> str:
    """Serialize a reviewable conversion dry run."""
    return json.dumps(snmp_walk_conversion_plan_data(plan), indent=2) + "\n"


def convert_snmp_walk(plan: SnmpWalkConversionPlan) -> SnmpConversionReceipt:
    """Convert declared walk text while preserving undecoded source evidence."""
    source = plan.input_path.resolve()
    output = plan.output_path.resolve()
    sidecar = output.with_suffix(output.suffix + ".unparsed.json")
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    if not source.is_file():
        raise SnmpConversionError(f"input recording does not exist: {source}")
    if source.stat().st_size > plan.max_input_bytes:
        raise SnmpConversionError("input recording exceeds max_input_bytes")
    checksum = _checksum(source)
    if checksum != plan.expected_sha256.lower():
        raise SnmpConversionError("input SHA-256 does not match the conversion plan")
    existing = [path for path in (output, sidecar, receipt_path) if path.exists()]
    if existing:
        raise SnmpConversionError(
            "conversion outputs already exist: "
            + ", ".join(str(path) for path in existing)
        )

    decoded = read_snmpwalk(source)
    if decoded.unparsed_lines and not plan.allow_unparsed_lines:
        raise SnmpConversionError(
            "input contains unparsed lines and the plan does not permit them"
        )
    canonical = "".join(
        f"{oid}|{value.type_code}|{value.value}\n"
        for oid, value in sorted(decoded.records.items(), key=_oid_key)
    ).encode("utf-8")
    unparsed_data = {
        "input_sha256": checksum,
        "lines": [asdict(item) for item in decoded.unparsed_lines],
    }
    receipt = SnmpConversionReceipt(
        input_path=str(source),
        output_path=str(output),
        input_format="net_snmp_walk",
        output_format="snmprec",
        input_sha256=checksum,
        output_sha256=hashlib.sha256(canonical).hexdigest(),
        record_count=len(decoded.records),
        unparsed_line_count=len(decoded.unparsed_lines),
        unparsed_sidecar_path=str(sidecar),
        source_url=plan.source_url,
        license=plan.license,
        device_category=plan.device_category,
        sanitized=plan.sanitized,
        approved_by=plan.approved_by,
        approved_at=plan.approved_at.isoformat(),
        rationale=plan.rationale,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    payloads = (
        (output, canonical),
        (sidecar, (json.dumps(unparsed_data, indent=2) + "\n").encode()),
        (receipt_path, (json.dumps(asdict(receipt), indent=2) + "\n").encode()),
    )
    temporary: list[tuple[Path, Path]] = []
    try:
        for destination, payload in payloads:
            temp = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
            temp.write_bytes(payload)
            temporary.append((temp, destination))
        for temp, destination in temporary:
            os.replace(temp, destination)
    finally:
        for temp, _ in temporary:
            temp.unlink(missing_ok=True)
    return receipt


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _oid_key(item: tuple[str, object]) -> tuple[int, ...]:
    return tuple(int(part) for part in item[0].split("."))
