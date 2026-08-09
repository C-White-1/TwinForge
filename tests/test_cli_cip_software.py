import json
from io import StringIO

from twinforge.cli import main


BASE_ARGUMENTS = (
    "discover",
    "software",
    "192.168.1.10",
    "--route-segment",
    "1/0",
    "--authorization-reference",
    "LAB-001",
    "--capability",
    "programs",
    "--capability",
    "tag_definitions",
    "--maximum-requests",
    "8",
)


def test_software_discovery_is_a_plan_only_dry_run_by_default() -> None:
    output = StringIO()
    errors = StringIO()

    exit_code = main(BASE_ARGUMENTS, stdout=output, stderr=errors)
    document = json.loads(output.getvalue())

    assert exit_code == 0
    assert errors.getvalue() == ""
    assert document["dry_run"] is True
    assert document["runtime_values_permitted"] is False
    assert document["maximum_requests"] == 8
    assert document["route"]["segments"] == [
        {"port": 1, "link_type": "integer", "link": 0}
    ]


def test_experimental_execution_requires_all_additional_confirmations() -> None:
    output = StringIO()
    errors = StringIO()

    exit_code = main(
        BASE_ARGUMENTS + ("--execute-experimental",),
        stdout=output,
        stderr=errors,
    )

    assert exit_code == 1
    assert output.getvalue() == ""
    assert "--confirmed-by" in errors.getvalue()
    assert "--confirmed-at" in errors.getvalue()
    assert "--laboratory-evidence-reference" in errors.getvalue()


def test_invalid_route_segment_is_reported_without_network_activity() -> None:
    arguments: list[str] = list(BASE_ARGUMENTS)
    arguments[4] = "not-a-route"
    output = StringIO()
    errors = StringIO()

    exit_code = main(tuple(arguments), stdout=output, stderr=errors)

    assert exit_code == 1
    assert "expected PORT/LINK" in errors.getvalue()
