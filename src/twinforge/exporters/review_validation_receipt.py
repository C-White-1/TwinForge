"""Deterministic receipts for validated engineering-review overlays."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


class ReviewValidationReceiptError(ValueError):
    """Raised when exact receipt evidence cannot be read."""


def review_validation_result_data(
    kind: str,
    review: Path,
    *,
    controller_name: str,
    item_count: int,
    source: Path | None = None,
    review_reference: str | None = None,
    source_reference: str | None = None,
) -> dict[str, object]:
    """Describe a successful validation using hashes of the exact inputs."""

    review_digest = _digest(review, "review")
    document: dict[str, object] = {
        "schema_version": "twinforge.review-validation-result.v1",
        "status": "valid",
        "review_kind": kind,
        "review_schema_version": f"twinforge.{kind}-review.v1",
        "review_path": review_reference or str(review),
        "review_sha256": review_digest,
        "controller_name": controller_name,
        "item_count": item_count,
        "source_reconciled": source is not None,
    }
    if source is not None:
        document.update(
            {
                "source_path": source_reference or str(source),
                "source_sha256": _digest(source, "L5X source"),
            }
        )
    return document


def review_validation_result_json(
    kind: str,
    review: Path,
    *,
    controller_name: str,
    item_count: int,
    source: Path | None = None,
    review_reference: str | None = None,
    source_reference: str | None = None,
) -> str:
    """Serialize one deterministic review-validation receipt."""

    return (
        json.dumps(
            review_validation_result_data(
                kind,
                review,
                controller_name=controller_name,
                item_count=item_count,
                source=source,
                review_reference=review_reference,
                source_reference=source_reference,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _digest(path: Path, label: str) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ReviewValidationReceiptError(
            f"cannot read {label} evidence '{path}': {error}"
        ) from error
