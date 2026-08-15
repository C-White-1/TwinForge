"""Deterministic integrity manifest for generated engineering reports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path


class ReportManifestError(ValueError):
    """Raised when manifest evidence cannot be read or represented."""


def verify_engineering_report_bundle(
    directory: Path,
    *,
    source: Path,
    alarm_review: Path | None = None,
    cause_effect_review: Path | None = None,
) -> tuple[int, int]:
    """Verify every manifested input and report against its recorded digest."""

    manifest_path = directory / "report_manifest.json"
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReportManifestError(
            f"cannot read report manifest '{manifest_path}': {error}"
        ) from error
    if not isinstance(document, dict) or document.get("schema_version") != (
        "twinforge.engineering-report-manifest.v1"
    ):
        raise ReportManifestError("unsupported or malformed report manifest")
    if document.get("hash_algorithm") != "sha256":
        raise ReportManifestError("report manifest hash_algorithm must be sha256")
    inputs = _records(document.get("inputs"), "inputs")
    reports = _records(document.get("reports"), "reports")
    supplied = {
        "l5x": source,
        **({"alarm_review": alarm_review} if alarm_review is not None else {}),
        **(
            {"cause_effect_review": cause_effect_review}
            if cause_effect_review is not None
            else {}
        ),
    }
    expected_kinds = {str(item.get("kind", "")) for item in inputs}
    if len(expected_kinds) != len(inputs):
        raise ReportManifestError("report manifest contains duplicate input kinds")
    if set(supplied) != expected_kinds:
        missing = sorted(expected_kinds - supplied.keys())
        extra = sorted(supplied.keys() - expected_kinds)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise ReportManifestError("manifest input mismatch: " + "; ".join(details))
    for record in inputs:
        kind = _required_string(record, "kind")
        _verify_file(supplied[kind], record, expected_name=False)

    listed_names = [_required_basename(item, "name") for item in reports]
    if len(listed_names) != len(set(listed_names)):
        raise ReportManifestError("report manifest contains duplicate report names")
    actual_names = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != "report_manifest.json"
    }
    if actual_names != set(listed_names):
        missing = sorted(set(listed_names) - actual_names)
        extra = sorted(actual_names - set(listed_names))
        raise ReportManifestError(
            "report file set mismatch: "
            + "; ".join(
                part
                for part in (
                    "missing " + ", ".join(missing) if missing else "",
                    "unexpected " + ", ".join(extra) if extra else "",
                )
                if part
            )
        )
    for record, name in zip(reports, listed_names, strict=True):
        _verify_file(directory / name, record, expected_name=True)
    return len(inputs), len(reports)


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


def _records(value: object, field: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ReportManifestError(f"report manifest {field} must be an array of objects")
    return value


def _required_string(record: dict[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise ReportManifestError(f"manifest record {field} must be a non-empty string")
    return value


def _required_basename(record: dict[str, object], field: str) -> str:
    value = _required_string(record, field)
    if Path(value).name != value or value in {".", ".."}:
        raise ReportManifestError(f"manifest report name is not a safe basename: {value!r}")
    return value


def _verify_file(
    path: Path,
    record: dict[str, object],
    *,
    expected_name: bool,
) -> None:
    if expected_name and path.name != _required_string(record, "name"):
        raise ReportManifestError(f"manifest filename mismatch for '{path}'")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ReportManifestError(f"cannot read manifested file '{path}': {error}") from error
    expected_size = record.get("size_bytes")
    expected_digest = record.get("sha256")
    if not isinstance(expected_size, int) or expected_size < 0:
        raise ReportManifestError("manifest size_bytes must be a non-negative integer")
    if (
        not isinstance(expected_digest, str)
        or len(expected_digest) != 64
        or any(character not in "0123456789abcdef" for character in expected_digest)
    ):
        raise ReportManifestError("manifest sha256 must be 64 lowercase hexadecimal characters")
    if len(content) != expected_size or sha256(content).hexdigest() != expected_digest:
        raise ReportManifestError(f"manifest integrity check failed for '{path}'")
