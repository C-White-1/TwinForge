from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from twinforge.exporters import engineering_report_manifest_json


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
