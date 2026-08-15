import json
from io import StringIO

from twinforge.cli import main


BASE_ARGUMENTS = (
    "discover",
    "identity",
    "127.0.0.1",
    "--engagement",
    "TwinForge controlled lab",
    "--authorization-reference",
    "LAB-IDENTITY-001",
)


def test_identity_discovery_is_a_plan_only_dry_run_by_default() -> None:
    output = StringIO()
    errors = StringIO()

    exit_code = main(BASE_ARGUMENTS, stdout=output, stderr=errors)
    document = json.loads(output.getvalue())

    assert exit_code == 0
    assert errors.getvalue() == ""
    assert document["dry_run"] is True
    assert document["operation"] == "cip_identity"
    assert document["total_request_budget"] == 1
    assert document["targets"] == [
        {
            "address": "127.0.0.1",
            "route": [],
            "label": None,
            "request_budget": 1,
        }
    ]


def test_identity_discovery_rejects_public_target_without_network_activity() -> None:
    arguments: list[str] = list(BASE_ARGUMENTS)
    arguments[2] = "8.8.8.8"
    output = StringIO()
    errors = StringIO()

    exit_code = main(tuple(arguments), stdout=output, stderr=errors)

    assert exit_code == 1
    assert output.getvalue() == ""
    assert "public target" in errors.getvalue()


def test_identity_discovery_rejects_unbounded_timeout() -> None:
    output = StringIO()
    errors = StringIO()

    exit_code = main(
        BASE_ARGUMENTS + ("--timeout", "11"),
        stdout=output,
        stderr=errors,
    )

    assert exit_code == 1
    assert output.getvalue() == ""
    assert "at most 10" in errors.getvalue()
