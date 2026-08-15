"""Deterministic integrity manifest for generated engineering reports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path


class ReportManifestError(ValueError):
    """Raised when manifest evidence cannot be read or represented."""


def engineering_report_manifest_json(
    source: Path,
    reports: Mapping[str, str],
    *,
    alarm_review: Path | None = None,
    cause_effect_review: Path | None = None,
) -> str:
    """Return a stable manifest covering source, overlays, and report content."""

    inputs = [_input_record("l5x", source)]
    if alarm_review is not None:
        inputs.append(_input_record("alarm_review", alarm_review))
    if cause_effect_review is not None:
        inputs.append(_input_record("cause_effect_review", cause_effect_review))
    document = {
        "schema_version": "twinforge.engineering-report-manifest.v1",
        "hash_algorithm": "sha256",
        "inputs": inputs,
        "reports": [
            {
                "name": name,
                "sha256": sha256(content.encode("utf-8")).hexdigest(),
                "size_bytes": len(content.encode("utf-8")),
            }
            for name, content in sorted(reports.items())
        ],
    }
    return json.dumps(document, indent=2) + "\n"


def _input_record(kind: str, path: Path) -> dict[str, object]:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ReportManifestError(
            f"cannot read {kind} manifest input '{path}': {error}"
        ) from error
    return {
        "kind": kind,
        "name": path.name,
        "sha256": sha256(content).hexdigest(),
        "size_bytes": len(content),
    }
