from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from io import StringIO

from twinforge.exporters import engineering_report_manifest_json
from twinforge.cli import main
from twinforge.exporters import TextReportBundle


def test_manifest_hashes_exact_input_and_generated_report_bytes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "controller.L5X"
    alarm_review = tmp_path / "alarm-review.json"
    source.write_bytes(b"<Controller/>\r\n")
    alarm_review.write_bytes(b'{"review":true}\n')
    reports = {"b.md": "beta\n", "a.csv": "alpha\n"}

    manifest = json.loads(
        engineering_report_manifest_json(
            source,
            reports,
            alarm_review=alarm_review,
        )
    )

    assert manifest["inputs"] == [
        {
            "kind": "l5x",
            "name": "controller.L5X",
            "sha256": sha256(source.read_bytes()).hexdigest(),
            "size_bytes": len(source.read_bytes()),
        },
        {
            "kind": "alarm_review",
            "name": "alarm-review.json",
            "sha256": sha256(alarm_review.read_bytes()).hexdigest(),
            "size_bytes": len(alarm_review.read_bytes()),
        },
    ]
    assert [item["name"] for item in manifest["reports"]] == ["a.csv", "b.md"]
    assert manifest["reports"][0]["sha256"] == sha256(b"alpha\n").hexdigest()


def test_manifest_is_reproducible_for_identical_inputs(tmp_path: Path) -> None:
    source = tmp_path / "controller.L5X"
    source.write_bytes(b"<Controller/>")
    reports = {"report.md": "evidence\n"}

    first = engineering_report_manifest_json(source, reports)
    second = engineering_report_manifest_json(source, reports)

    assert first == second


def test_cli_verification_fails_after_report_is_modified(tmp_path: Path) -> None:
    source = tmp_path / "controller.L5X"
    source.write_bytes(b"<Controller/>")
    reports = {"report.md": "original\n"}
    reports["report_manifest.json"] = engineering_report_manifest_json(
        source,
        reports,
    )
    destination = tmp_path / "reports"
    TextReportBundle(reports).write_to(destination)
    (destination / "report.md").write_text(
        "modified\n",
        encoding="utf-8",
        newline="",
    )
    errors = StringIO()

    result = main(
        (
            "reports",
            "verify",
            str(destination),
            "--source",
            str(source),
        ),
        stderr=errors,
    )

    assert result == 1
    assert "integrity check failed" in errors.getvalue()


def test_cli_verification_requires_every_manifested_review(tmp_path: Path) -> None:
    source = tmp_path / "controller.L5X"
    review = tmp_path / "alarm-review.json"
    source.write_bytes(b"<Controller/>")
    review.write_bytes(b"{}")
    reports = {"report.md": "original\n"}
    reports["report_manifest.json"] = engineering_report_manifest_json(
        source,
        reports,
        alarm_review=review,
    )
    destination = tmp_path / "reports"
    TextReportBundle(reports).write_to(destination)
    errors = StringIO()

    result = main(
        (
            "reports",
            "verify",
            str(destination),
            "--source",
            str(source),
        ),
        stderr=errors,
    )

    assert result == 1
    assert "missing alarm_review" in errors.getvalue()
