"""CLI coverage for local EDS catalogue queries."""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from io import StringIO
from pathlib import Path

from twinforge.cli import main


def _export(tmp_path: Path) -> Path:
    root = tmp_path / "ExportEDSAll"
    eds = root / "EDS"
    database = eds / "Database" / "export.db"
    database.parent.mkdir(parents=True)
    source = eds / "00010007000B0300.eds"
    source.write_text(
        """
[Device]
VendCode = 1;
VendName = "Allen-Bradley";
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
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE EDSInfo (
            EDSASAKey TEXT, VendorName TEXT, ProductName TEXT, DefaultIcon TEXT,
            EDSFileName TEXT, TopologyCatalog TEXT, MajorVersion INTEGER,
            MinorVersion INTEGER, Ports TEXT, SHA256 TEXT, Capabilities TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO EDSInfo VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "key",
                "Allen-Bradley",
                "1756-IB16/A",
                None,
                source.name,
                "1756-IB16/A",
                3,
                1,
                None,
                digest,
                None,
            ),
        )
    return root


def test_base_catalog_query_writes_promoted_json(tmp_path: Path) -> None:
    root = _export(tmp_path)
    output = StringIO()

    result = main(
        [
            "catalog",
            "eds",
            "--root",
            str(root),
            "--base-catalog-number",
            "1756-IB16",
            "--format",
            "json",
        ],
        stdout=output,
        stderr=StringIO(),
    )

    document = json.loads(output.getvalue())
    assert result == 0
    assert document["count"] == 1
    assert document["query"] == {
        "kind": "base_catalog_number",
        "value": "1756-IB16",
    }
    assert document["records"][0]["catalog_number"] == "1756-IB16/A"
    assert document["records"][0]["identity"]["vendor_id"] == 1
    assert "raw_fields" not in document["records"][0]


def test_missing_export_reports_stable_command_error(tmp_path: Path) -> None:
    errors = StringIO()

    result = main(
        [
            "catalog",
            "eds",
            "--root",
            str(tmp_path),
            "--catalog-number",
            "1756-IB16/A",
        ],
        stdout=StringIO(),
        stderr=errors,
    )

    assert result == 1
    assert "export database does not exist" in errors.getvalue()
