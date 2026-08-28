"""Electronic-key reconciliation over neutral catalogue candidates."""

from pathlib import Path

from twinforge.knowledge.catalog_reconciliation import (
    CatalogCandidateStatus,
    reconcile_catalog_candidates,
)
from twinforge.knowledge.device_catalog import DeviceCatalogRecord
from twinforge.model import (
    ElectronicKey,
    Identity,
    KeyingMode,
    Revision,
    VendorIdentity,
)


def _identity(major: int, minor: int, *, product_code: int = 11) -> Identity:
    return Identity(
        vendor=VendorIdentity(1),
        product_type=7,
        product_code=product_code,
        revision=Revision(major, minor),
    )


def _record(major: int, minor: int, *, product_code: int = 11) -> DeviceCatalogRecord:
    return DeviceCatalogRecord(
        source_key=f"{major}.{minor}",
        source_file=Path(f"revision-{major}-{minor}.eds"),
        catalog_number="1756-IB16/A",
        identity=_identity(major, minor, product_code=product_code),
    )


def test_exact_key_selects_one_unique_full_identity_match() -> None:
    result = reconcile_catalog_candidates(
        ElectronicKey(mode=KeyingMode.EXACT_MATCH, identity=_identity(3, 1)),
        (_record(2, 1), _record(3, 1)),
    )

    assert result.selected == result.candidates[1].record
    assert [item.status for item in result.candidates] == [
        CatalogCandidateStatus.CONFLICT,
        CatalogCandidateStatus.EXACT,
    ]


def test_exact_key_retains_ambiguity_when_duplicate_matches_exist() -> None:
    result = reconcile_catalog_candidates(
        ElectronicKey(mode=KeyingMode.EXACT_MATCH, identity=_identity(3, 1)),
        (_record(3, 1), _record(3, 1)),
    )

    assert result.selected is None
    assert "unique" in result.rationale


def test_compatible_key_is_advisory_even_for_typical_revision() -> None:
    result = reconcile_catalog_candidates(
        ElectronicKey(
            mode=KeyingMode.COMPATIBLE_MODULE,
            identity=_identity(2, 1),
        ),
        (_record(2, 1), _record(3, 1), _record(3, 1, product_code=12)),
    )

    assert result.selected is None
    assert [item.status for item in result.candidates] == [
        CatalogCandidateStatus.TYPICAL_COMPATIBLE,
        CatalogCandidateStatus.TYPICAL_COMPATIBLE,
        CatalogCandidateStatus.CONFLICT,
    ]
    assert "device acceptance" in result.rationale


def test_missing_or_disabled_key_never_selects_a_candidate() -> None:
    records = (_record(3, 1),)

    missing = reconcile_catalog_candidates(None, records)
    disabled = reconcile_catalog_candidates(
        ElectronicKey(mode=KeyingMode.DISABLED),
        records,
    )

    assert missing.selected is None
    assert disabled.selected is None
    assert missing.candidates[0].status is CatalogCandidateStatus.UNRESOLVED
    assert disabled.candidates[0].status is CatalogCandidateStatus.UNRESOLVED
