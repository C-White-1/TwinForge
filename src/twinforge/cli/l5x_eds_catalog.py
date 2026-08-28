"""Offline L5X-to-EDS catalogue reconciliation command adapter."""

from __future__ import annotations

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from importlib.resources import files
from pathlib import Path
from typing import TextIO

from twinforge.analysis.eds_catalog_reconciliation import (
    ModuleCatalogAssessment,
    assess_controller_eds_catalog,
)
from twinforge.knowledge.eds_cache import (
    EdsExportCatalogError,
    RockwellEdsExportCatalog,
)
from twinforge.model import Controller
from twinforge.parsers.l5x import L5XParser


class L5XEdsCatalogCommandError(RuntimeError):
    """An L5X catalogue assessment could not be completed."""


def reconcile_l5x_eds_catalog(
    source: Path,
    export_root: Path,
    *,
    output_format: str,
    verify_hashes: bool,
    destination: Path | None = None,
    stdout: TextIO,
) -> None:
    """Reconcile configured modules against a local EDS export."""

    try:
        document = L5XParser().parse_document(source, report_mode=None)
        if not isinstance(document.target, Controller):
            raise L5XEdsCatalogCommandError(
                "EDS catalogue reconciliation requires a Controller L5X target"
            )
        catalog = RockwellEdsExportCatalog(
            export_root,
            verify_hashes=verify_hashes,
        )
        assessments = assess_controller_eds_catalog(document.target, catalog)
    except (ET.ParseError, OSError, ValueError, EdsExportCatalogError) as error:
        raise L5XEdsCatalogCommandError(
            f"cannot reconcile L5X with EDS catalogue: {error}"
        ) from error

    result = {
        "schema_version": "twinforge.eds-catalog-reconciliation.v1",
        "source": str(source),
        "catalog_root": str(catalog.export_root),
        "controller": document.target.name,
        "module_count": len(assessments),
        "modules": [_assessment_json(item) for item in assessments],
    }
    content = (
        json.dumps(result, indent=2, sort_keys=True) + "\n"
        if output_format == "json"
        else _text_report(document.target.name, assessments)
    )
    if destination is None:
        stdout.write(content)
    else:
        try:
            _write_atomic(destination, content)
        except OSError as error:
            raise L5XEdsCatalogCommandError(
                f"could not write EDS catalogue reconciliation '{destination}': "
                f"{error}"
            ) from error
        stdout.write(f"Wrote EDS catalogue reconciliation to {destination}\n")


def eds_catalog_reconciliation_schema_text() -> str:
    """Return the exact packaged reconciliation JSON Schema."""

    return (
        files("twinforge.schemas")
        .joinpath("eds-catalog-reconciliation.v1.schema.json")
        .read_text(encoding="utf-8")
    )


def export_eds_catalog_reconciliation_schema(
    destination: Path,
    *,
    stdout: TextIO,
) -> None:
    """Export the installed reconciliation schema."""

    try:
        _write_atomic(destination, eds_catalog_reconciliation_schema_text())
    except OSError as error:
        raise L5XEdsCatalogCommandError(
            f"could not export EDS catalogue schema to '{destination}': {error}"
        ) from error
    stdout.write(f"Exported EDS catalogue reconciliation schema to {destination}\n")


def _text_report(
    controller_name: str,
    assessments: tuple[ModuleCatalogAssessment, ...],
) -> str:
    lines = [
        f"Controller: {controller_name}",
        f"Configured modules: {len(assessments)}",
    ]
    for item in assessments:
        module = item.module
        lines.append(
            f"- {module.name} [{module.catalog}] "
            f"slot/address={module.slot if module.slot is not None else module.address or '-'} "
            f"status={item.status.value} "
            f"candidates={len(item.reconciliation.candidates)}"
        )
    return "\n".join(lines) + "\n"


def _write_atomic(destination: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            temporary = Path(stream.name)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _assessment_json(item: ModuleCatalogAssessment) -> dict[str, object]:
    module = item.module
    selected = item.reconciliation.selected
    return {
        "chassis": item.chassis,
        "module": module.name,
        "catalog_number": module.catalog,
        "slot": module.slot,
        "address": module.address,
        "keying_mode": (
            module.electronic_key.mode.value
            if module.electronic_key and module.electronic_key.mode
            else module.electronic_key.unknown_mode
            if module.electronic_key
            else None
        ),
        "status": item.status.value,
        "rationale": item.reconciliation.rationale,
        "selected_eds": str(selected.source_file) if selected else None,
        "candidates": [
            {
                "eds": str(candidate.record.source_file),
                "catalog_number": candidate.record.catalog_number,
                "revision": (
                    str(candidate.record.identity.revision)
                    if candidate.record.identity.revision
                    else None
                ),
                "status": candidate.status.value,
                "matched_fields": list(candidate.matched_fields),
                "conflicting_fields": list(candidate.conflicting_fields),
                "unavailable_fields": list(candidate.unavailable_fields),
                "rationale": candidate.rationale,
            }
            for candidate in item.reconciliation.candidates
        ],
    }
