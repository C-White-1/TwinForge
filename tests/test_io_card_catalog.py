"""Coverage for the versioned, user-authored I/O card library."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from twinforge.knowledge.io_card_catalog import (
    IOCardLibrary,
    IOCardLibraryError,
    io_card_library_schema_text,
    load_io_card_library,
)


def _document() -> dict:
    return {
        "schema_version": "twinforge.io-card-library.v1",
        "cards": [
            {
                "part_number": "P2-16ND3-1",
                "vendor": "AutomationDirect",
                "direction": "Input",
                "signal_type": "Digital",
                "channel_count": 16,
                "voltage": "12-24VDC",
                "description": "16-point sinking/sourcing discrete input",
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


def test_library_loads_and_finds_cards_case_insensitively() -> None:
    library = IOCardLibrary.model_validate(_document())

    found = library.find("p2-16nd3-1")
    assert found is not None
    assert found.channel_count == 16
    assert library.find("P2-16ND3-1") is not None
    assert library.find("unknown") is None


def test_library_rejects_duplicate_part_numbers() -> None:
    document = _document()
    document["cards"].append(dict(document["cards"][0]))

    with pytest.raises(ValidationError, match="unique"):
        IOCardLibrary.model_validate(document)


def test_library_rejects_blank_part_number() -> None:
    document = _document()
    document["cards"][0]["part_number"] = "   "

    with pytest.raises(ValidationError, match="blank"):
        IOCardLibrary.model_validate(document)


def test_load_io_card_library_reads_from_disk(tmp_path: Path) -> None:
    path = tmp_path / "io-card-library.json"
    path.write_text(json.dumps(_document()), encoding="utf-8")

    library = load_io_card_library(path)

    assert len(library.cards) == 2


def test_load_io_card_library_wraps_errors(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(IOCardLibraryError):
        load_io_card_library(path)


def test_io_card_library_schema_text_is_valid_json_schema() -> None:
    schema = json.loads(io_card_library_schema_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_document())
