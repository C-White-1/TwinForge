"""Tests for deterministic neutral-model JSON evidence export."""

from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import re

from twinforge.cli import main
import pytest

from twinforge.exporters import (
    ModelJSONExporter,
    ModelJSONPointerError,
    ModelJSONValidationError,
    model_json_schema_text,
    resolve_model_json_pointer,
    validate_model_json,
)
from jsonschema import Draft202012Validator
from twinforge.model import (
    Controller,
    Identity,
    Program,
    Routine,
    SourceExtension,
    SourceNode,
)
from twinforge.parsers.l5x.document import L5XDocument, L5XTargetType


DATA = Path(__file__).parent / "data"


def _document() -> L5XDocument:
    controller = Controller(name="Controller", identity=Identity())
    program = Program(name="MainProgram")
    program.add_routine(
        Routine(
            name="MainRoutine",
            metadata={1: "slot-one", "$ref": "source-value"},
        )
    )
    controller.add_program(program)
    return L5XDocument(
        target_type=L5XTargetType.CONTROLLER,
        target_name=controller.name,
        target=controller,
        source_path=Path("fixture.L5X"),
        source_extensions=(
            SourceExtension(
                format="l5x",
                root=SourceNode(
                    name="Controller",
                    attributes={"FutureAttribute": "retained"},
                ),
            ),
        ),
    )


def test_model_json_is_deterministic_and_preserves_references_and_source() -> None:
    first = ModelJSONExporter().export(_document())
    second = ModelJSONExporter().export(_document())

    assert first == second
    payload = json.loads(first)
    target = payload["document"]["target"]
    assert "id" not in target
    routine = target["programs"]["MainProgram"]["main_routine"]
    assert routine == {
        "$ref": "#/document/target/programs/MainProgram/routines/MainRoutine"
    }
    extension = payload["document"]["source_extensions"][0]
    assert extension["root"]["attributes"]["FutureAttribute"] == "retained"
    routine_metadata = target["programs"]["MainProgram"]["routines"][
        "MainRoutine"
    ]["metadata"]
    assert routine_metadata == {
        "$map": [
            {"key": "$ref", "value": "source-value"},
            {"key": 1, "value": "slot-one"},
        ]
    }
    assert validate_model_json(first) == payload


def test_packaged_model_json_schema_accepts_exported_evidence() -> None:
    schema = json.loads(model_json_schema_text())
    Draft202012Validator.check_schema(schema)

    Draft202012Validator(schema).validate(
        json.loads(ModelJSONExporter().export(_document()))
    )


def test_model_json_pointer_selects_and_resolves_evidence() -> None:
    exported = ModelJSONExporter().export(_document())
    pointer = (
        "#/document/target/programs/MainProgram/routines/MainRoutine/metadata"
        "/$map/0/value"
    )
    assert resolve_model_json_pointer(exported, pointer) == "source-value"

    reference = (
        "#/document/target/programs/MainProgram/main_routine"
    )
    selected = resolve_model_json_pointer(exported, reference)
    assert selected == {
        "$ref": "#/document/target/programs/MainProgram/routines/MainRoutine"
    }
    resolved = resolve_model_json_pointer(
        exported,
        reference,
        resolve_reference=True,
    )
    assert resolved["name"] == "MainRoutine"
    escaped = resolve_model_json_pointer(
        exported,
        "#/document/source_extensions/0/root/attributes/Future%41ttribute",
    )
    assert escaped == "retained"


@pytest.mark.parametrize(
    "pointer",
    (
        "/document",
        "#/document/not-there",
        "#/document/~2bad",
        "#/document/%ZZ",
        "#/document/source_extensions/01",
    ),
)
def test_model_json_pointer_rejects_invalid_or_missing_paths(
    pointer: str,
) -> None:
    with pytest.raises(ModelJSONPointerError):
        resolve_model_json_pointer(ModelJSONExporter().export(_document()), pointer)


@pytest.mark.parametrize(
    "replacement, message",
    (
        ({"$ref": "not-a-pointer"}, "invalid $ref"),
        ({"$bytes_hex": "not-hex"}, "invalid $bytes_hex"),
        ({"$map": [{"key": "missing-value"}]}, "invalid map entry"),
        ({"$type": "", "name": "bad"}, "blank $type"),
    ),
)
def test_model_json_validator_rejects_malformed_control_objects(
    replacement: dict[str, object],
    message: str,
) -> None:
    payload = json.loads(ModelJSONExporter().export(_document()))
    payload["document"]["target"] = replacement

    with pytest.raises(ModelJSONValidationError, match=re.escape(message)):
        validate_model_json(payload)


@pytest.mark.parametrize(
    "reference",
    (
        "#/document/not_present",
        "#/document/source_extensions",
    ),
)
def test_model_json_validator_rejects_dangling_and_forward_references(
    reference: str,
) -> None:
    payload = json.loads(ModelJSONExporter().export(_document()))
    payload["document"]["target"] = {"$ref": reference}

    with pytest.raises(
        ModelJSONValidationError,
        match="unresolved or forward \\$ref",
    ):
        validate_model_json(payload)


def test_cli_exports_standalone_l5x_model_json(tmp_path: Path) -> None:
    destination = tmp_path / "module.json"
    output = StringIO()

    result = main(
        (
            "export",
            str(DATA / "standalone/module.L5X"),
            "--target",
            "json",
            "--output",
            str(destination),
        ),
        stdout=output,
    )

    assert result == 0
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["document"]["target_type"] == "Module"
    assert "Exported neutral model JSON" in output.getvalue()


def test_cli_json_dry_run_does_not_write_output(tmp_path: Path) -> None:
    destination = tmp_path / "module.json"

    result = main(
        (
            "export",
            str(DATA / "standalone/module.L5X"),
            "--target",
            "json",
            "--output",
            str(destination),
            "--dry-run",
        )
    )

    assert result == 0
    assert not destination.exists()
