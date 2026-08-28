"""Synthetic tests for the local Rockwell EDS export adapter."""

from __future__ import annotations

import base64
import hashlib
import sqlite3
from pathlib import Path

import pytest

from twinforge.knowledge.eds_cache import (
    EdsExportCatalogError,
    RockwellEdsExportCatalog,
)

_COLUMNS = """
EDSASAKey TEXT, VendorName TEXT, ProductName TEXT, DefaultIcon TEXT,
EDSFileName TEXT, TopologyCatalog TEXT, MajorVersion INTEGER,
MinorVersion INTEGER, Ports TEXT, SHA256 TEXT, Capabilities TEXT
"""


def _create_export(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "ExportEDSAll"
    eds_directory = root / "EDS"
    database_directory = eds_directory / "Database"
    icon_directory = eds_directory / "Icons"
    database_directory.mkdir(parents=True)
    icon_directory.mkdir()
    source = eds_directory / "00010007000B0301.eds"
    source.write_text(
        """
[Device]
VendCode = 1;
VendName = "Rockwell Automation/Allen-Bradley";
ProdType = 7;
ProdTypeStr = "Digital I/O";
ProdCode = 11;
MajRev = 3;
MinRev = 1;
ProdName = "1756-IB16";
""",
        encoding="utf-8",
    )
    digest = base64.b64encode(hashlib.sha256(source.read_bytes()).digest()).decode()
    database = database_directory / "export.db"
    with sqlite3.connect(database) as connection:
        connection.execute(f"CREATE TABLE EDSInfo ({_COLUMNS})")
        connection.execute(
            "INSERT INTO EDSInfo VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "synthetic-key",
                "Rockwell Automation/Allen-Bradley",
                "1756-IB16",
                "input.ico",
                source.name,
                "1756-IB16",
                3,
                1,
                "Port1",
                digest,
                "Synthetic capability",
            ),
        )
    return root, source


def test_finds_catalog_and_promotes_authoritative_eds_identity(tmp_path: Path) -> None:
    root, source = _create_export(tmp_path)

    records = RockwellEdsExportCatalog(root).find_by_catalog_number(" 1756-ib16 ")

    assert len(records) == 1
    record = records[0]
    assert record.source_file == source
    assert record.source_key == "synthetic-key"
    assert record.catalog_number == "1756-IB16"
    assert record.manufacturer == "Allen-Bradley / Rockwell Automation"
    assert record.identity.vendor is not None
    assert record.identity.vendor.id == 1
    assert record.identity.product_type == 7
    assert record.identity.product_code == 11
    assert record.identity.product_name == "1756-IB16"
    assert record.raw_fields["VendorName"] == "Rockwell Automation/Allen-Bradley"
    assert record.ports == "Port1"
    assert record.capabilities == "Synthetic capability"


def test_returns_all_exact_product_name_matches(tmp_path: Path) -> None:
    root, _ = _create_export(tmp_path)

    records = RockwellEdsExportCatalog(root).find_by_product_name("1756-ib16")

    assert len(records) == 1
    assert RockwellEdsExportCatalog(root).find_by_catalog_number("1756-IF8") == ()


def test_base_catalog_lookup_accepts_series_suffix_only(tmp_path: Path) -> None:
    root, _ = _create_export(tmp_path)
    database = root / "EDS" / "Database" / "export.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE EDSInfo SET TopologyCatalog = '1756-IB16/A'"
        )

    catalog = RockwellEdsExportCatalog(root)

    assert len(catalog.find_by_base_catalog_number("1756-IB16")) == 1
    assert catalog.find_by_base_catalog_number("1756-IB16D") == ()


def test_rejects_hash_mismatch_before_parsing(tmp_path: Path) -> None:
    root, source = _create_export(tmp_path)
    source.write_text("changed", encoding="utf-8")

    with pytest.raises(EdsExportCatalogError, match="SHA-256 mismatch"):
        RockwellEdsExportCatalog(root).find_by_catalog_number("1756-IB16")


def test_rejects_missing_database_and_incompatible_schema(tmp_path: Path) -> None:
    with pytest.raises(EdsExportCatalogError, match="does not exist"):
        RockwellEdsExportCatalog(tmp_path)

    database = tmp_path / "EDS" / "Database" / "export.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE EDSInfo (EDSFileName TEXT)")

    with pytest.raises(EdsExportCatalogError, match="missing required columns"):
        RockwellEdsExportCatalog(tmp_path)
