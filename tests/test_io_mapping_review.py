"""Coverage for applying an attributable physical I/O mapping review."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from twinforge.analysis.io_mapping_review import (
    IOMappingReviewDocument,
    IOMappingReviewError,
    apply_io_mapping_review,
)
from twinforge.knowledge.io_card_catalog import IOCardLibrary


def _library() -> IOCardLibrary:
    return IOCardLibrary.model_validate(
        {
            "schema_version": "twinforge.io-card-library.v1",
            "cards": [
                {
                    "part_number": "P2-16ND3-1",
                    "vendor": "AutomationDirect",
                    "direction": "Input",
                    "signal_type": "Digital",
                    "channel_count": 16,
                },
                {
                    "part_number": "P2-16TD1P",
                    "vendor": "AutomationDirect",
                    "direction": "Output",
                    "signal_type": "Digital",
                    "channel_count": 16,
                },
            ],
        }
    )


def _points() -> list[dict[str, object]]:
    return [
        {
            "physical_address": "_IO_EM_DI_00",
            "direction": "Input",
            "signal_type": "Digital",
            "data_type": "BOOL",
            "assignment_status": "assigned",
            "variable_names": ["IN00"],
            "aliases": ["Stop_PB"],
        },
        {
            "physical_address": "_IO_EM_DO_00",
            "direction": "Output",
            "signal_type": "Digital",
            "data_type": "BOOL",
            "assignment_status": "assigned",
            "variable_names": ["OUT00"],
            "aliases": ["Size_Fault"],
        },
        {
            "physical_address": "_IO_EM_XX_09",
            "direction": None,
            "signal_type": None,
            "data_type": None,
            "assignment_status": "spare",
            "variable_names": [],
            "aliases": [],
        },
    ]


def _review(*items: dict[str, object]) -> IOMappingReviewDocument:
    return IOMappingReviewDocument.model_validate(
        {
            "schema_version": "twinforge.io-mapping-review.v1",
            "controller_name": "M10 Conveyor",
            "reviewed_by": "Control systems engineer",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "authority_reference": "Design review",
            "source_reference": "reference/ccw-tests/M10_Conveyor.json",
            "items": list(items),
        }
    )


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "physical_address": "_IO_EM_DI_00",
        "card_part_number": "P2-16ND3-1",
        "card_instance": "DI-1",
        "channel": 0,
    }
    base.update(overrides)
    return base


def test_resolves_known_points_and_leaves_the_rest_unmapped() -> None:
    review = _review(_item())

    report = apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)

    assert len(report.resolved) == 1
    resolution = report.resolved[0]
    assert resolution.physical_address == "_IO_EM_DI_00"
    assert resolution.card_part_number == "P2-16ND3-1"
    assert resolution.compatibility_confirmed is True
    assert report.unmapped == ("_IO_EM_DO_00", "_IO_EM_XX_09")


def test_allows_a_spare_point_to_be_mapped() -> None:
    review = _review(_item(), _item(physical_address="_IO_EM_DO_00", card_part_number="P2-16TD1P", card_instance="DO-1"))

    report = apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)

    assert len(report.resolved) == 2
    assert report.unmapped == ("_IO_EM_XX_09",)


def test_allows_binding_a_point_with_unknown_direction_but_flags_it_unconfirmed() -> None:
    review = _review(
        _item(physical_address="_IO_EM_XX_09", card_part_number="P2-16ND3-1", channel=5)
    )

    report = apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)

    assert report.resolved[0].compatibility_confirmed is False


def test_rejects_mismatched_controller_name() -> None:
    review = IOMappingReviewDocument.model_validate(
        {
            "schema_version": "twinforge.io-mapping-review.v1",
            "controller_name": "Some Other Controller",
            "reviewed_by": "Control systems engineer",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "authority_reference": "Design review",
            "source_reference": "reference/ccw-tests/M10_Conveyor.json",
            "items": [_item()],
        }
    )

    with pytest.raises(IOMappingReviewError, match="controller_name"):
        apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)


def test_rejects_unknown_physical_address() -> None:
    review = _review(_item(physical_address="_IO_EM_DI_99"))

    with pytest.raises(IOMappingReviewError, match="unknown physical_address"):
        apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)


def test_rejects_unknown_card_part_number() -> None:
    review = _review(_item(card_part_number="NOT-A-REAL-CARD"))

    with pytest.raises(IOMappingReviewError, match="unknown card_part_number"):
        apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)


def test_rejects_channel_out_of_range() -> None:
    review = _review(_item(channel=16))

    with pytest.raises(IOMappingReviewError, match="channel_count"):
        apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)


def test_rejects_incompatible_direction() -> None:
    review = _review(_item(card_part_number="P2-16TD1P", card_instance="DO-1"))

    with pytest.raises(IOMappingReviewError, match="incompatible"):
        apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)


def test_rejects_duplicate_channel_assignment() -> None:
    review = _review(
        _item(),
        _item(physical_address="_IO_EM_XX_09"),
    )

    with pytest.raises(IOMappingReviewError, match="same card channel"):
        apply_io_mapping_review("M10 Conveyor", _points(), _library(), review)


def test_document_rejects_duplicate_physical_address() -> None:
    with pytest.raises(ValidationError, match="unique"):
        _review(_item(), _item(card_instance="DI-2", channel=1))
