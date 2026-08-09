"""Conservative evaluation of configured electronic-key evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from twinforge.model import Identity, KeyingMode, Module

from .contracts import CipIdentityObservation


class ElectronicKeyVerdict(str, Enum):
    """Outcome that distinguishes decisions from evidence requiring review."""

    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    SATISFIED = "satisfied"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class ElectronicKeyEvaluation:
    """Specification-attributed keying result without compatibility guesses."""

    verdict: ElectronicKeyVerdict
    mode: str | None
    matched_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    unavailable_fields: tuple[str, ...]
    typical_compatible_revision: bool | None
    rationale: str
    evidence_references: tuple[str, ...]


def electronic_key_evaluation_data(
    evaluation: ElectronicKeyEvaluation,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible keying evaluation."""
    return {
        "verdict": evaluation.verdict.value,
        "mode": evaluation.mode,
        "matched_fields": list(evaluation.matched_fields),
        "conflicting_fields": list(evaluation.conflicting_fields),
        "unavailable_fields": list(evaluation.unavailable_fields),
        "typical_compatible_revision": (
            evaluation.typical_compatible_revision
        ),
        "rationale": evaluation.rationale,
        "evidence_references": list(evaluation.evidence_references),
    }


_KEY_FIELDS = (
    "vendor_id",
    "device_type",
    "product_code",
    "major_revision",
    "minor_revision",
)

_IMPORT_EXPORT_REFERENCE = (
    "Rockwell Automation 1756-RM014D-EN-P (September 2025), "
    "Module State and keying attributes"
)
_KEYING_TECHNIQUE_REFERENCE = (
    "Rockwell Automation LOGIX-AT001A-EN-P (September 2014), "
    "Electronic Keying in Logix5000 Control Systems"
)


def evaluate_electronic_key(
    module: Module,
    discovered: CipIdentityObservation,
) -> ElectronicKeyEvaluation:
    """Evaluate only outcomes supported by retained identity evidence."""
    key = module.electronic_key
    if key is None:
        return _result(
            ElectronicKeyVerdict.NOT_CONFIGURED,
            None,
            rationale="the configured module contains no electronic key",
        )
    mode = key.mode.value if key.mode is not None else key.unknown_mode
    if key.mode is KeyingMode.DISABLED:
        return _result(
            ElectronicKeyVerdict.DISABLED,
            mode,
            rationale="configured electronic keying is disabled",
        )

    expected = key.identity if key.identity is not None else module.identity
    matched, conflicting, unavailable = _compare(expected, discovered)
    common = {
        "mode": mode,
        "matched_fields": matched,
        "conflicting_fields": conflicting,
        "unavailable_fields": unavailable,
    }
    if key.mode is KeyingMode.EXACT_MATCH:
        if unavailable:
            return _result(
                ElectronicKeyVerdict.DEFERRED,
                rationale="exact keying evidence is incomplete",
                **common,
            )
        if conflicting:
            return _result(
                ElectronicKeyVerdict.REJECTED,
                rationale="one or more exact keying attributes conflict",
                **common,
            )
        return _result(
            ElectronicKeyVerdict.SATISFIED,
            rationale="all five exact keying attributes match",
            **common,
        )

    if key.mode is KeyingMode.COMPATIBLE_MODULE:
        typical = _typical_compatible_revision(expected, discovered)
        return _result(
            ElectronicKeyVerdict.DEFERRED,
            typical_compatible_revision=typical,
            rationale=(
                "Compatible Module is decided by the device and product family; "
                "the numeric comparison is advisory only"
            ),
            **common,
        )
    if key.mode is KeyingMode.CUSTOM:
        return _result(
            ElectronicKeyVerdict.DEFERRED,
            rationale=(
                "custom key attributes were compared, but no retained rule "
                "defines their acceptance semantics"
            ),
            **common,
        )
    return _result(
        ElectronicKeyVerdict.DEFERRED,
        rationale="the source electronic-key mode is unknown",
        **common,
    )


def _compare(
    expected: Identity,
    discovered: CipIdentityObservation,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    configured = _identity_values(expected)
    observed = {
        "vendor_id": discovered.vendor_id,
        "device_type": discovered.device_type,
        "product_code": discovered.product_code,
        "major_revision": discovered.major_revision,
        "minor_revision": discovered.minor_revision,
    }
    matched: list[str] = []
    conflicting: list[str] = []
    unavailable: list[str] = []
    for field in _KEY_FIELDS:
        if field not in configured:
            unavailable.append(field)
        elif configured[field] == observed[field]:
            matched.append(field)
        else:
            conflicting.append(field)
    return tuple(matched), tuple(conflicting), tuple(unavailable)


def _identity_values(identity: Identity) -> dict[str, int]:
    values: dict[str, int] = {}
    if identity.vendor is not None:
        values["vendor_id"] = identity.vendor.id
    if identity.product_type is not None:
        values["device_type"] = identity.product_type
    if identity.product_code is not None:
        values["product_code"] = identity.product_code
    if identity.revision is not None:
        values["major_revision"] = identity.revision.major
        values["minor_revision"] = identity.revision.minor
    return values


def _typical_compatible_revision(
    expected: Identity,
    discovered: CipIdentityObservation,
) -> bool | None:
    values = _identity_values(expected)
    if any(field not in values for field in _KEY_FIELDS):
        return None
    if (
        values["vendor_id"] != discovered.vendor_id
        or values["device_type"] != discovered.device_type
        or values["product_code"] != discovered.product_code
    ):
        return False
    configured_major = values["major_revision"]
    if discovered.major_revision < configured_major:
        return False
    return (
        discovered.major_revision > configured_major
        or discovered.minor_revision >= values["minor_revision"]
    )


def _result(
    verdict: ElectronicKeyVerdict,
    mode: str | None,
    *,
    rationale: str,
    matched_fields: tuple[str, ...] = (),
    conflicting_fields: tuple[str, ...] = (),
    unavailable_fields: tuple[str, ...] = (),
    typical_compatible_revision: bool | None = None,
) -> ElectronicKeyEvaluation:
    return ElectronicKeyEvaluation(
        verdict=verdict,
        mode=mode,
        matched_fields=matched_fields,
        conflicting_fields=conflicting_fields,
        unavailable_fields=unavailable_fields,
        typical_compatible_revision=typical_compatible_revision,
        rationale=rationale,
        evidence_references=(
            _IMPORT_EXPORT_REFERENCE,
            _KEYING_TECHNIQUE_REFERENCE,
        ),
    )
