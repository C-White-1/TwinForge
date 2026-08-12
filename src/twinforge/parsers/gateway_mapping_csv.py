"""Evidence-preserving CSV ingestion for manually supplied gateway mappings."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity


@dataclass(frozen=True)
class GatewayMappingRecord:
    """One CSV mapping row, including unknown source columns."""

    row_number: int
    mapping_id: str | None
    source_interface: str | None
    source_reference: str | None
    target_interface: str | None
    target_reference: str | None
    evidence: str | None
    values: tuple[tuple[str, str], ...] = field(repr=False)

    @property
    def promotable(self) -> bool:
        """Return whether the row contains the minimum mapping evidence."""

        return all(
            value is not None
            for value in (
                self.source_interface,
                self.target_interface,
                self.evidence,
            )
        )

    @property
    def metadata(self) -> dict[str, str]:
        """Return columns not consumed by the neutral mapping contract."""

        known = {
            "mapping_id",
            "source_interface",
            "source_reference",
            "target_interface",
            "target_reference",
            "evidence",
        }
        return {name: value for name, value in self.values if name not in known}


@dataclass(frozen=True)
class GatewayMappingCSVDocument:
    """One CSV mapping document with all rows retained in source order."""

    source_path: Path
    headers: tuple[str, ...]
    records: tuple[GatewayMappingRecord, ...]
    diagnostics: tuple[ConversionDiagnostic, ...] = ()


class GatewayMappingCSVParser:
    """Parse TwinForge's neutral gateway-mapping CSV interchange format."""

    def parse(self, filename: str | Path) -> GatewayMappingCSVDocument:
        """Parse a CSV file and diagnose rows lacking required evidence."""

        path = Path(filename)
        diagnostics: list[ConversionDiagnostic] = []
        records: list[GatewayMappingRecord] = []
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = tuple(reader.fieldnames or ())
            for row_number, row in enumerate(reader, start=2):
                values = tuple(
                    (name, value or "")
                    for name, value in row.items()
                    if name is not None
                )
                record = GatewayMappingRecord(
                    row_number=row_number,
                    mapping_id=_optional(row.get("mapping_id")),
                    source_interface=_optional(row.get("source_interface")),
                    source_reference=_optional(row.get("source_reference")),
                    target_interface=_optional(row.get("target_interface")),
                    target_reference=_optional(row.get("target_reference")),
                    evidence=_optional(row.get("evidence")),
                    values=values,
                )
                records.append(record)
                missing = tuple(
                    name
                    for name, value in (
                        ("source_interface", record.source_interface),
                        ("target_interface", record.target_interface),
                        ("evidence", record.evidence),
                    )
                    if value is None
                )
                if missing:
                    diagnostics.append(
                        ConversionDiagnostic(
                            severity=DiagnosticSeverity.WARNING,
                            code="gateway_mapping_required_value_missing",
                            message=(
                                f"gateway mapping CSV row {row_number} is missing "
                                f"{', '.join(missing)}"
                            ),
                            object_name=record.mapping_id,
                            field=",".join(missing),
                        )
                    )
        return GatewayMappingCSVDocument(
            source_path=path,
            headers=headers,
            records=tuple(records),
            diagnostics=tuple(diagnostics),
        )


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
