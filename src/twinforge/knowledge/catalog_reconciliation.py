"""Conservative reconciliation of catalogue records with electronic keys."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from twinforge.model import ElectronicKey, Identity, KeyingMode

from .device_catalog import DeviceCatalogRecord

_FIELDS = (
    "vendor_id",
    "product_type",
    "product_code",
    "major_revision",
    "minor_revision",
)


class CatalogCandidateStatus(str, Enum):
    """Evidence status for one indexed device-description candidate."""

    EXACT = "exact"
    TYPICAL_COMPATIBLE = "typical_compatible"
    CONFLICT = "conflict"
    INCOMPLETE = "incomplete"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class CatalogCandidateEvaluation:
    """Field-level comparison of one catalogue record."""

    record: DeviceCatalogRecord
    status: CatalogCandidateStatus
    matched_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    unavailable_fields: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class CatalogReconciliation:
    """Catalogue candidates plus any uniquely justified exact selection."""

    candidates: tuple[CatalogCandidateEvaluation, ...]
    selected: DeviceCatalogRecord | None
    rationale: str


def reconcile_catalog_candidates(
    electronic_key: ElectronicKey | None,
    candidates: tuple[DeviceCatalogRecord, ...],
    *,
    fallback_identity: Identity | None = None,
) -> CatalogReconciliation:
    """Compare EDS identities without inventing vendor compatibility rules."""

    if electronic_key is None:
        return _unresolved(candidates, "no configured electronic key")
    mode = electronic_key.mode
    if mode is KeyingMode.DISABLED:
        return _unresolved(candidates, "configured electronic keying is disabled")
    expected = electronic_key.identity or fallback_identity
    if expected is None:
        return _unresolved(candidates, "configured key identity is unavailable")
    if (
        mode is not KeyingMode.EXACT_MATCH
        and mode is not KeyingMode.COMPATIBLE_MODULE
    ):
        return _unresolved(
            candidates,
            "custom or unknown keying semantics require manual review",
        )

    evaluations = tuple(
        _evaluate(expected, candidate, mode)
        for candidate in candidates
    )
    if mode is KeyingMode.EXACT_MATCH:
        exact = tuple(
            item for item in evaluations if item.status is CatalogCandidateStatus.EXACT
        )
        if len(exact) == 1:
            return CatalogReconciliation(
                candidates=evaluations,
                selected=exact[0].record,
                rationale="one EDS candidate satisfies all exact key fields",
            )
        return CatalogReconciliation(
            candidates=evaluations,
            selected=None,
            rationale=(
                "exact keying did not produce one unique fully matching candidate"
            ),
        )
    return CatalogReconciliation(
        candidates=evaluations,
        selected=None,
        rationale=(
            "Compatible Module candidates are advisory; device acceptance and "
            "product-family rules are not inferred from the catalogue"
        ),
    )


def _evaluate(
    expected: Identity,
    candidate: DeviceCatalogRecord,
    mode: KeyingMode,
) -> CatalogCandidateEvaluation:
    configured = _identity_values(expected)
    observed = _identity_values(candidate.identity)
    matched: list[str] = []
    conflicting: list[str] = []
    unavailable: list[str] = []
    for field in _FIELDS:
        if field not in configured or field not in observed:
            unavailable.append(field)
        elif configured[field] == observed[field]:
            matched.append(field)
        else:
            conflicting.append(field)
    if unavailable:
        status = CatalogCandidateStatus.INCOMPLETE
        rationale = "one or more electronic-key fields are unavailable"
    elif mode is KeyingMode.EXACT_MATCH:
        status = (
            CatalogCandidateStatus.CONFLICT
            if conflicting
            else CatalogCandidateStatus.EXACT
        )
        rationale = (
            "one or more exact key fields conflict"
            if conflicting
            else "all exact key fields match"
        )
    else:
        compatible = _typical_compatible(configured, observed)
        status = (
            CatalogCandidateStatus.TYPICAL_COMPATIBLE
            if compatible
            else CatalogCandidateStatus.CONFLICT
        )
        rationale = (
            "numeric identity follows the typical compatible-revision pattern"
            if compatible
            else "numeric identity conflicts with the typical compatibility pattern"
        )
    return CatalogCandidateEvaluation(
        record=candidate,
        status=status,
        matched_fields=tuple(matched),
        conflicting_fields=tuple(conflicting),
        unavailable_fields=tuple(unavailable),
        rationale=rationale,
    )


def _identity_values(identity: Identity) -> dict[str, int]:
    values: dict[str, int] = {}
    if identity.vendor is not None:
        values["vendor_id"] = identity.vendor.id
    if identity.product_type is not None:
        values["product_type"] = identity.product_type
    if identity.product_code is not None:
        values["product_code"] = identity.product_code
    if identity.revision is not None:
        values["major_revision"] = identity.revision.major
        values["minor_revision"] = identity.revision.minor
    return values


def _typical_compatible(expected: dict[str, int], candidate: dict[str, int]) -> bool:
    if any(
        expected[field] != candidate[field]
        for field in ("vendor_id", "product_type", "product_code")
    ):
        return False
    if candidate["major_revision"] < expected["major_revision"]:
        return False
    return (
        candidate["major_revision"] > expected["major_revision"]
        or candidate["minor_revision"] >= expected["minor_revision"]
    )


def _unresolved(
    candidates: tuple[DeviceCatalogRecord, ...],
    rationale: str,
) -> CatalogReconciliation:
    return CatalogReconciliation(
        candidates=tuple(
            CatalogCandidateEvaluation(
                record=record,
                status=CatalogCandidateStatus.UNRESOLVED,
                matched_fields=(),
                conflicting_fields=(),
                unavailable_fields=_FIELDS,
                rationale=rationale,
            )
            for record in candidates
        ),
        selected=None,
        rationale=rationale,
    )
