"""Offline compatibility measurement for explicitly sourced SNMP recordings."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .contracts import DiscoveryTarget
from .snmprec import (
    SnmprecSizeLimitError,
    build_snmp_node,
    read_snmprec_recording,
)
from .snmpwalk import read_snmpwalk
from .snmp_oid_coverage import (
    count_snmp_oid_families,
    lowered_snmp_oid_families,
)
from .snmp_entity import validate_entity_containment


class SnmpCorpusEntry(BaseModel):
    """Provenance and local location of one externally sourced recording."""

    model_config = ConfigDict(frozen=True)

    identifier: str = Field(min_length=1)
    path: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    license: str = Field(min_length=1)
    device_category: str = Field(min_length=1)
    sha256: str | None = None
    sanitized: bool = False

    @field_validator(
        "identifier", "path", "source_url", "license", "device_category"
    )
    @classmethod
    def text_must_be_trimmed(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("corpus text must not contain surrounding whitespace")
        return value

    @field_validator("sha256")
    @classmethod
    def checksum_must_be_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lower()
        if len(normalized) != 64 or any(
            character not in "0123456789abcdef" for character in normalized
        ):
            raise ValueError("sha256 must contain 64 hexadecimal characters")
        return normalized


class SnmpCorpusManifest(BaseModel):
    """Reviewable boundary around recordings that are not owned by TwinForge."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    entries: tuple[SnmpCorpusEntry, ...]

    @field_validator("entries")
    @classmethod
    def identifiers_must_be_unique(
        cls, value: tuple[SnmpCorpusEntry, ...]
    ) -> tuple[SnmpCorpusEntry, ...]:
        identifiers = [entry.identifier for entry in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("corpus entry identifiers must be unique")
        return value


@dataclass(frozen=True)
class SnmpCorpusResult:
    """Compatibility evidence for one manifest entry."""

    identifier: str
    status: str
    format: str
    oid_count: int
    system_fields: int
    interfaces: int
    addresses: int
    neighbours: int
    forwarding_entries: int
    physical_entities: int
    entity_containment_issues: int
    unparsed_lines: int
    oid_families: dict[str, int]
    sha256: str | None
    message: str | None = None


@dataclass(frozen=True)
class SnmpCorpusReport:
    """Deterministically ordered results for one corpus run."""

    schema_version: str
    max_recording_bytes: int
    results: tuple[SnmpCorpusResult, ...]


def discover_snmp_corpus(
    root: str | Path,
    *,
    source_url: str,
    license_name: str,
    sanitized: bool = False,
    path_base: str | Path | None = None,
) -> SnmpCorpusManifest:
    """Describe recognized recordings below ``root`` without copying them."""
    directory = Path(root).resolve()
    base = directory if path_base is None else Path(path_base).resolve()
    paths = sorted(
        (
            path
            for path in directory.rglob("*")
            if path.is_file()
            and (
                path.name.lower().endswith(".snmprec")
                or path.name.lower().endswith(".snmprec.bz2")
                or path.name.lower().endswith(".snmpwalk")
            )
        ),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    entries = tuple(
        SnmpCorpusEntry(
            identifier=path.relative_to(directory).as_posix(),
            path=Path(os.path.relpath(path, base)).as_posix(),
            source_url=source_url,
            license=license_name,
            device_category=(
                path.relative_to(directory).parts[0]
                if len(path.relative_to(directory).parts) > 1
                else "unclassified"
            ),
            sha256=_checksum(path),
            sanitized=sanitized,
        )
        for path in paths
    )
    return SnmpCorpusManifest(entries=entries)


def load_snmp_corpus_manifest(path: str | Path) -> SnmpCorpusManifest:
    """Load and validate a JSON corpus manifest."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SnmpCorpusManifest.model_validate(data)


def snmp_corpus_manifest_json(manifest: SnmpCorpusManifest) -> str:
    """Serialize a manifest deterministically for review and later reuse."""
    return json.dumps(
        manifest.model_dump(mode="json"),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _failure(
    entry: SnmpCorpusEntry,
    *,
    status: str,
    format_name: str,
    message: str,
    checksum: str | None = None,
) -> SnmpCorpusResult:
    return SnmpCorpusResult(
        identifier=entry.identifier,
        status=status,
        format=format_name,
        oid_count=0,
        system_fields=0,
        interfaces=0,
        addresses=0,
        neighbours=0,
        forwarding_entries=0,
        physical_entities=0,
        entity_containment_issues=0,
        unparsed_lines=0,
        oid_families={},
        sha256=checksum,
        message=message,
    )


def measure_snmp_corpus(
    manifest: SnmpCorpusManifest,
    manifest_path: str | Path,
    *,
    max_recording_bytes: int = 16 * 1024 * 1024,
) -> SnmpCorpusReport:
    """Measure supported evidence without opening a network connection."""
    if max_recording_bytes < 1:
        raise ValueError("max_recording_bytes must be positive")
    base = Path(manifest_path).resolve().parent
    results: list[SnmpCorpusResult] = []
    captured_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    for entry in sorted(manifest.entries, key=lambda item: item.identifier):
        recording = (base / entry.path).resolve()
        lower_name = recording.name.lower()
        format_name = (
            "snmprec.bz2"
            if lower_name.endswith(".snmprec.bz2")
            else recording.suffix.lower().lstrip(".") or "unknown"
        )
        if not recording.is_file():
            results.append(
                _failure(
                    entry,
                    status="missing",
                    format_name=format_name,
                    message=f"recording does not exist: {recording}",
                )
            )
            continue
        checksum = _checksum(recording)
        if entry.sha256 is not None and checksum != entry.sha256:
            results.append(
                _failure(
                    entry,
                    status="checksum_mismatch",
                    format_name=format_name,
                    checksum=checksum,
                    message="recording SHA-256 does not match the manifest",
                )
            )
            continue
        is_snmprec = lower_name.endswith((".snmprec", ".snmprec.bz2"))
        if not is_snmprec and recording.suffix.lower() != ".snmpwalk":
            results.append(
                _failure(
                    entry,
                    status="unsupported_format",
                    format_name=format_name,
                    checksum=checksum,
                    message=(
                        "supported formats are .snmprec, .snmprec.bz2 and "
                        ".snmpwalk"
                    ),
                )
            )
            continue
        try:
            unparsed_lines = 0
            if recording.suffix.lower() == ".snmpwalk":
                decoded = read_snmpwalk(recording)
                records = decoded.records
                unparsed_lines = len(decoded.unparsed_lines)
            else:
                decoded = read_snmprec_recording(
                    recording,
                    max_bytes=max_recording_bytes,
                )
                records = decoded.records
                unparsed_lines = len(decoded.unparsed_lines)
            node = build_snmp_node(
                DiscoveryTarget(address=f"fixture:{entry.identifier}"),
                captured_at,
                records,
            )
        except SnmprecSizeLimitError as error:
            results.append(
                _failure(
                    entry,
                    status="resource_limit",
                    format_name=format_name,
                    checksum=checksum,
                    message=str(error),
                )
            )
            continue
        except (OSError, UnicodeError, ValueError) as error:
            results.append(
                _failure(
                    entry,
                    status="parse_error",
                    format_name=format_name,
                    checksum=checksum,
                    message=str(error),
                )
            )
            continue
        system_fields = sum(
            value is not None
            for value in (
                node.system_name,
                node.system_description,
                node.system_object_id,
                node.system_contact,
                node.system_location,
                node.uptime_ticks,
            )
        )
        results.append(
            SnmpCorpusResult(
                identifier=entry.identifier,
                status="measured",
                format=format_name,
                oid_count=len(records),
                system_fields=system_fields,
                interfaces=len(node.interfaces),
                addresses=sum(
                    len(interface.addresses) for interface in node.interfaces
                ),
                neighbours=len(node.neighbours),
                forwarding_entries=len(node.forwarding_entries),
                physical_entities=len(node.physical_entities),
                entity_containment_issues=len(
                    validate_entity_containment(node.physical_entities)
                ),
                unparsed_lines=unparsed_lines,
                oid_families=count_snmp_oid_families(records),
                sha256=checksum,
                message=(
                    f"retained {unparsed_lines} unparsed line(s)"
                    if unparsed_lines
                    else None
                ),
            )
        )
    return SnmpCorpusReport(
        schema_version="1",
        max_recording_bytes=max_recording_bytes,
        results=tuple(results),
    )


def snmp_corpus_data(report: SnmpCorpusReport) -> dict[str, Any]:
    """Return a stable JSON-compatible report representation."""
    return {
        "schema_version": report.schema_version,
        "max_recording_bytes": report.max_recording_bytes,
        "results": [asdict(result) for result in report.results],
    }


def snmp_corpus_json(report: SnmpCorpusReport) -> str:
    """Serialize a compatibility report as deterministic JSON."""
    return json.dumps(snmp_corpus_data(report), indent=2) + "\n"


def aggregate_snmp_oid_families(report: SnmpCorpusReport) -> dict[str, int]:
    """Aggregate per-recording family counts in deterministic key order."""
    totals: dict[str, int] = {}
    for result in report.results:
        for family, count in result.oid_families.items():
            totals[family] = totals.get(family, 0) + count
    return dict(sorted(totals.items()))


def snmp_corpus_markdown(report: SnmpCorpusReport) -> str:
    """Render a compact, markdownlint-compatible compatibility report."""
    measured = sum(result.status == "measured" for result in report.results)
    lines = [
        "# SNMP Recording Compatibility Report",
        "",
        f"- Recordings: {len(report.results)}",
        f"- Successfully measured: {measured}",
        f"- Per-recording byte limit: {report.max_recording_bytes}",
        "- Network access: none",
        "",
        "| Recording | Status | Format | OIDs | System | Interfaces | "
        "Addresses | Neighbours | FDB | Entities | Entity issues | Unparsed |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: |",
    ]
    for result in report.results:
        lines.append(
            f"| {result.identifier} | {result.status} | {result.format} | "
            f"{result.oid_count} | {result.system_fields} | "
            f"{result.interfaces} | {result.addresses} | "
            f"{result.neighbours} | {result.forwarding_entries} | "
            f"{result.physical_entities} | "
            f"{result.entity_containment_issues} | "
            f"{result.unparsed_lines} |"
        )
    family_counts = aggregate_snmp_oid_families(report)
    lowered = set(lowered_snmp_oid_families())
    if family_counts:
        lines.extend(
            [
                "",
                "## OID family coverage",
                "",
                "| Family | OIDs | Semantically lowered |",
                "| --- | ---: | --- |",
            ]
        )
        for family, count in sorted(
            family_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            lines.append(
                f"| `{family}` | {count} | "
                f"{'Yes' if family in lowered else 'No'} |"
            )
    messages = [result for result in report.results if result.message]
    if messages:
        lines.extend(["", "## Diagnostics", ""])
        lines.extend(
            f"- `{result.identifier}`: {result.message}" for result in messages
        )
    return "\n".join(lines) + "\n"
