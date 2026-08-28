"""Read-only access to Rockwell's locally installed EDS export catalogue."""

from __future__ import annotations

import base64
import hashlib
import hmac
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from twinforge.parsers.eds import EDSParser

from .device_catalog import DeviceCatalogRecord
from .vendor import canonical_vendor_name

_DATABASE_RELATIVE_PATH = Path("EDS") / "Database" / "export.db"
_EDS_DIRECTORY = Path("EDS")
_REQUIRED_COLUMNS = frozenset(
    {
        "EDSASAKey",
        "VendorName",
        "ProductName",
        "DefaultIcon",
        "EDSFileName",
        "TopologyCatalog",
        "MajorVersion",
        "MinorVersion",
        "Ports",
        "SHA256",
        "Capabilities",
    }
)


class EdsExportCatalogError(RuntimeError):
    """A local EDS export cannot be queried or verified safely."""


class RockwellEdsExportCatalog:
    """Adapt a Rockwell Export EDS All directory through a read-only boundary.

    The SQLite database is treated as an index. Authoritative CIP identity is
    promoted by parsing the referenced EDS, not inferred from its filename or
    duplicated database text.
    """

    def __init__(self, export_root: str | Path, *, verify_hashes: bool = True) -> None:
        self._root = Path(export_root).resolve()
        self._database = self._root / _DATABASE_RELATIVE_PATH
        self._verify_hashes = verify_hashes
        if not self._database.is_file():
            raise EdsExportCatalogError(
                f"Rockwell EDS export database does not exist: {self._database}"
            )
        self._validate_schema()

    @property
    def export_root(self) -> Path:
        """Return the local export root without transferring its contents."""

        return self._root

    def find_by_catalog_number(
        self,
        catalog_number: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        """Return exact, case-insensitive matches from ``TopologyCatalog``."""

        expected = catalog_number.strip()
        if not expected:
            return ()
        sql = (
            "SELECT * FROM EDSInfo "
            "WHERE TopologyCatalog IS NOT NULL "
            "AND lower(trim(TopologyCatalog)) = lower(?) "
            "ORDER BY EDSFileName"
        )
        with self._connect() as connection:
            rows = connection.execute(sql, (expected,)).fetchall()
        return tuple(self._promote(row) for row in rows)

    def find_by_product_name(
        self,
        product_name: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        """Return exact, case-insensitive product-name matches."""

        expected = product_name.strip()
        if not expected:
            return ()
        sql = (
            "SELECT * FROM EDSInfo "
            "WHERE ProductName IS NOT NULL "
            "AND lower(trim(ProductName)) = lower(?) "
            "ORDER BY EDSFileName"
        )
        with self._connect() as connection:
            rows = connection.execute(sql, (expected,)).fetchall()
        return tuple(self._promote(row) for row in rows)

    def find_by_base_catalog_number(
        self,
        catalog_number: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        """Match a base catalog number and optional Rockwell ``/series`` suffix.

        For example, ``1756-IB16`` matches ``1756-IB16/A`` but does not match
        related products such as ``1756-IB16D/A``. Callers receive every EDS
        revision because selecting compatibility is a separate decision.
        """

        expected = catalog_number.strip().rstrip("/")
        if not expected:
            return ()
        sql = (
            "SELECT * FROM EDSInfo "
            "WHERE TopologyCatalog IS NOT NULL "
            "AND (lower(trim(TopologyCatalog)) = lower(?) "
            "OR lower(trim(TopologyCatalog)) LIKE lower(?)) "
            "ORDER BY EDSFileName"
        )
        with self._connect() as connection:
            rows = connection.execute(
                sql,
                (expected, f"{expected}/%"),
            ).fetchall()
        return tuple(self._promote(row) for row in rows)

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self._database.as_posix()}?mode=ro&immutable=1"
        try:
            connection = sqlite3.connect(uri, uri=True)
        except sqlite3.Error as error:
            raise EdsExportCatalogError(
                f"could not open EDS export database read-only: {error}"
            ) from error
        connection.row_factory = sqlite3.Row
        return connection

    def _validate_schema(self) -> None:
        try:
            with self._connect() as connection:
                columns = {
                    str(row[1])
                    for row in connection.execute("PRAGMA table_info(EDSInfo)")
                }
        except sqlite3.Error as error:
            raise EdsExportCatalogError(
                f"could not inspect EDS export schema: {error}"
            ) from error
        missing = sorted(_REQUIRED_COLUMNS - columns)
        if missing:
            raise EdsExportCatalogError(
                "EDSInfo is missing required columns: " + ", ".join(missing)
            )

    def _promote(self, row: sqlite3.Row) -> DeviceCatalogRecord:
        raw = MappingProxyType(dict(row))
        filename = _required_text(raw, "EDSFileName")
        source = _safe_child(self._root / _EDS_DIRECTORY, filename)
        if not source.is_file():
            raise EdsExportCatalogError(f"indexed EDS file does not exist: {source}")
        if self._verify_hashes:
            _verify_digest(source, _required_text(raw, "SHA256"))
        document = EDSParser().parse(source)
        identity = document.identity
        source_vendor = _text(raw.get("VendorName"))
        vendor_id = identity.vendor.id if identity.vendor is not None else None
        manufacturer = canonical_vendor_name(vendor_id, source_vendor)
        if identity.vendor is not None:
            identity.vendor = type(identity.vendor)(identity.vendor.id, manufacturer)
        icon_text = _text(raw.get("DefaultIcon"))
        icon = (
            _safe_child(self._root / _EDS_DIRECTORY / "Icons", icon_text)
            if icon_text
            else None
        )
        return DeviceCatalogRecord(
            source_key=_required_text(raw, "EDSASAKey"),
            source_file=source,
            identity=identity,
            manufacturer=manufacturer,
            catalog_number=_text(raw.get("TopologyCatalog")),
            default_icon=icon,
            ports=_text(raw.get("Ports")),
            capabilities=_text(raw.get("Capabilities")),
            raw_fields=raw,
        )


def _safe_child(parent: Path, relative_name: str) -> Path:
    candidate = (parent / relative_name).resolve()
    try:
        candidate.relative_to(parent.resolve())
    except ValueError as error:
        raise EdsExportCatalogError(
            f"catalogue path escapes its expected directory: {relative_name!r}"
        ) from error
    return candidate


def _verify_digest(source: Path, expected_base64: str) -> None:
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = base64.b64encode(digest.digest()).decode("ascii")
    if not hmac.compare_digest(actual, expected_base64):
        raise EdsExportCatalogError(f"EDS SHA-256 mismatch: {source}")


def _required_text(row: Mapping[str, object | None], name: str) -> str:
    value = _text(row.get(name))
    if value is None:
        raise EdsExportCatalogError(f"EDSInfo.{name} is empty")
    return value


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
