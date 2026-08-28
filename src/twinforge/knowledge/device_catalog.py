"""Vendor-neutral contracts for local device-description catalogues."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Protocol

from twinforge.model import Identity


@dataclass(frozen=True, kw_only=True)
class DeviceCatalogRecord:
    """One device-description record promoted from a local catalogue.

    Source-specific fields remain available in ``raw_fields`` so promotion
    never discards evidence that the neutral model does not yet understand.
    """

    source_key: str
    source_file: Path
    identity: Identity
    manufacturer: str | None = None
    catalog_number: str | None = None
    default_icon: Path | None = None
    ports: str | None = None
    capabilities: str | None = None
    raw_fields: Mapping[str, object | None] = field(default_factory=dict)


class DeviceCatalog(Protocol):
    """Read-only lookup boundary implemented by device catalogues."""

    def find_by_catalog_number(
        self,
        catalog_number: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        """Return every exact catalogue-number match."""

        ...


class BaseCatalogDeviceCatalog(DeviceCatalog, Protocol):
    """Catalogue that understands a vendor's explicit series suffix syntax."""

    def find_by_base_catalog_number(
        self,
        catalog_number: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        """Return exact base-catalog matches without fuzzy family guessing."""

        ...
