"""User-facing queries over a locally installed EDS export catalogue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from twinforge.knowledge.device_catalog import DeviceCatalogRecord
from twinforge.knowledge.eds_cache import (
    EdsExportCatalogError,
    RockwellEdsExportCatalog,
)


class EdsCatalogCommandError(RuntimeError):
    """An EDS catalogue query could not be completed safely."""


def query_eds_catalog(
    export_root: Path,
    *,
    catalog_number: str | None = None,
    base_catalog_number: str | None = None,
    product_name: str | None = None,
    output_format: str = "text",
    verify_hashes: bool = True,
    stdout: TextIO,
) -> None:
    """Query local indexed EDS metadata and write neutral promoted records."""

    try:
        catalog = RockwellEdsExportCatalog(
            export_root,
            verify_hashes=verify_hashes,
        )
        if catalog_number is not None:
            query_kind = "catalog_number"
            query_value = catalog_number
            records = catalog.find_by_catalog_number(catalog_number)
        elif base_catalog_number is not None:
            query_kind = "base_catalog_number"
            query_value = base_catalog_number
            records = catalog.find_by_base_catalog_number(base_catalog_number)
        elif product_name is not None:
            query_kind = "product_name"
            query_value = product_name
            records = catalog.find_by_product_name(product_name)
        else:
            raise EdsCatalogCommandError("one EDS catalogue query is required")
    except EdsExportCatalogError as error:
        raise EdsCatalogCommandError(str(error)) from error

    if output_format == "json":
        document = {
            "schema_version": "1.0",
            "source": str(catalog.export_root),
            "query": {"kind": query_kind, "value": query_value},
            "count": len(records),
            "records": [_record_json(record) for record in records],
        }
        stdout.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
        return
    stdout.write(
        f"EDS catalogue query: {query_kind}={query_value!r}\n"
        f"Matches: {len(records)}\n"
    )
    for record in records:
        _write_text_record(record, stdout)


def _record_json(record: DeviceCatalogRecord) -> dict[str, object | None]:
    identity = record.identity
    return {
        "source_key": record.source_key,
        "source_file": str(record.source_file),
        "catalog_number": record.catalog_number,
        "manufacturer": record.manufacturer,
        "default_icon": str(record.default_icon) if record.default_icon else None,
        "ports": record.ports,
        "capabilities": record.capabilities,
        "identity": {
            "vendor_id": identity.vendor.id if identity.vendor else None,
            "vendor_name": identity.vendor.name if identity.vendor else None,
            "product_type": identity.product_type,
            "product_type_name": identity.product_type_name,
            "product_code": identity.product_code,
            "product_name": identity.product_name,
            "major_revision": identity.revision.major if identity.revision else None,
            "minor_revision": identity.revision.minor if identity.revision else None,
        },
    }


def _write_text_record(record: DeviceCatalogRecord, stdout: TextIO) -> None:
    identity = record.identity
    revision = str(identity.revision) if identity.revision else "-"
    vendor_id = str(identity.vendor.id) if identity.vendor else "-"
    stdout.write(
        "\n"
        f"Catalog: {record.catalog_number or '-'}\n"
        f"Product: {identity.product_name or '-'}\n"
        f"Manufacturer: {record.manufacturer or '-'}\n"
        f"CIP identity: vendor {vendor_id}, type "
        f"{identity.product_type if identity.product_type is not None else '-'}, "
        f"code {identity.product_code if identity.product_code is not None else '-'}, "
        f"revision {revision}\n"
        f"EDS: {record.source_file}\n"
    )
