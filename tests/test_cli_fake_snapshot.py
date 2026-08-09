import json
from io import StringIO
from pathlib import Path

from twinforge.cli import main


ARGUMENTS = (
    "discover",
    "fake-snapshot",
    "--engagement",
    "sanitized-demo",
    "--authorization-reference",
    "DEMO-ONLY",
    "--captured-at",
    "2026-08-09T00:00:00+00:00",
)


def test_fake_snapshot_cli_is_socket_free_and_matches_checked_fixture() -> None:
    output = StringIO()
    errors = StringIO()

    exit_code = main(ARGUMENTS, stdout=output, stderr=errors)
    expected = (
        Path(__file__).parents[1]
        / "examples/discovery/sanitized-fake-snapshot.json"
    ).read_text(encoding="utf-8")

    assert exit_code == 0
    assert errors.getvalue() == ""
    assert output.getvalue() == expected
    document = json.loads(output.getvalue())
    assert document["engagement"] == "sanitized-demo"
    assert document["identities"][0]["raw_attributes"]["sanitized"] is True


def test_fake_snapshot_requires_timezone_qualified_capture_time() -> None:
    output = StringIO()
    errors = StringIO()
    arguments = ARGUMENTS[:-1] + ("2026-08-09T00:00:00",)

    exit_code = main(arguments, stdout=output, stderr=errors)

    assert exit_code == 1
    assert output.getvalue() == ""
    assert "timezone" in errors.getvalue()
