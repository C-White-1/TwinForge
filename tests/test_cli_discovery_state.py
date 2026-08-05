from io import StringIO
import json

from twinforge.cli import main


def test_state_init_validate_and_json_inspect(tmp_path) -> None:
    path = tmp_path / "state/discovery.json"
    output = StringIO()
    errors = StringIO()

    assert main(
        ("state", "init", str(path)), stdout=output, stderr=errors
    ) == 0
    assert path.is_file()
    assert "revision 1" in output.getvalue()
    assert errors.getvalue() == ""

    output = StringIO()
    assert main(
        ("state", "validate", str(path)), stdout=output, stderr=errors
    ) == 0
    assert "Valid TwinForge discovery state 1.0, revision 1." in output.getvalue()

    output = StringIO()
    assert main(
        ("state", "inspect", str(path), "--format", "json"),
        stdout=output,
        stderr=errors,
    ) == 0
    summary = json.loads(output.getvalue())
    assert summary == {
        "schema_version": "1.0",
        "revision": 1,
        "active_identity_keys": [],
        "inactive_identity_keys": [],
        "generation_count": 0,
        "event_count": 0,
        "promotion_count": 0,
        "promoted_asset_ids": [],
        "unpromoted_identity_keys": [],
    }


def test_state_init_refuses_overwrite_and_missing_inspect_is_an_error(
    tmp_path,
) -> None:
    path = tmp_path / "discovery.json"
    assert main(("state", "init", str(path))) == 0
    output = StringIO()
    errors = StringIO()

    assert main(
        ("state", "init", str(path)), stdout=output, stderr=errors
    ) == 1
    assert "refusing to overwrite" in errors.getvalue()

    errors = StringIO()
    assert main(
        ("state", "inspect", str(tmp_path / "missing.json")),
        stdout=output,
        stderr=errors,
    ) == 1
    assert "does not exist" in errors.getvalue()


def test_state_validate_reports_malformed_document(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version": "99.0"}', encoding="utf-8")
    output = StringIO()
    errors = StringIO()

    assert main(
        ("state", "validate", str(path)), stdout=output, stderr=errors
    ) == 1
    assert output.getvalue() == ""
    assert "invalid discovery state document" in errors.getvalue()
