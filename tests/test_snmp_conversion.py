import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from io import StringIO

from twinforge.discovery import (
    SnmpConversionError,
    SnmpWalkConversionPlan,
    convert_snmp_walk,
    read_snmprec_recording,
    snmp_walk_conversion_plan_json,
)
from twinforge.cli import main


NOW = datetime(2026, 8, 10, tzinfo=timezone.utc)


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "vendor-unusual.dump"
    path.write_text(
        "SNMPv2-MIB::sysName.0 = STRING: switch-01\n"
        "VENDOR-MIB::unknownThing.0 = STRING: retained\n"
        "IF-MIB::ifIndex.1 = INTEGER: 1\n",
        encoding="utf-8",
    )
    return path


def _plan(source: Path, output: Path, **changes: object) -> SnmpWalkConversionPlan:
    values: dict[str, object] = {
        "input_path": source,
        "output_path": output,
        "expected_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_url": "https://example.invalid/authorized-fixture",
        "license": "BSD-2-Clause",
        "device_category": "switch",
        "sanitized": True,
        "approved_by": "lab.operator",
        "approved_at": NOW,
        "rationale": "Declared vendor dump as Net-SNMP walk text",
    }
    values.update(changes)
    return SnmpWalkConversionPlan(**values)  # type: ignore[arg-type]


def test_dry_run_is_explicit_and_performs_no_conversion(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "converted.snmprec"
    document = json.loads(snmp_walk_conversion_plan_json(_plan(source, output)))

    assert document["dry_run"] is True
    assert document["operation"] == "convert_net_snmp_walk"
    assert document["network_access"] is False
    assert document["overwrite"] is False
    assert not output.exists()


def test_conversion_retains_canonical_records_and_unparsed_evidence(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "converted.snmprec"

    receipt = convert_snmp_walk(_plan(source, output))
    decoded = read_snmprec_recording(output)
    sidecar = json.loads(
        output.with_suffix(".snmprec.unparsed.json").read_text(encoding="utf-8")
    )

    assert receipt.record_count == 2
    assert receipt.unparsed_line_count == 1
    assert decoded.records["1.3.6.1.2.1.1.5.0"].value == "switch-01"
    assert sidecar["lines"][0]["text"].endswith("STRING: retained")
    assert output.with_suffix(".snmprec.receipt.json").is_file()


def test_checksum_mismatch_fails_without_outputs(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "converted.snmprec"

    with pytest.raises(SnmpConversionError, match="SHA-256"):
        convert_snmp_walk(_plan(source, output, expected_sha256="0" * 64))

    assert not output.exists()


def test_unparsed_policy_and_no_overwrite_are_enforced(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "converted.snmprec"
    with pytest.raises(SnmpConversionError, match="does not permit"):
        convert_snmp_walk(_plan(source, output, allow_unparsed_lines=False))

    convert_snmp_walk(_plan(source, output))
    with pytest.raises(SnmpConversionError, match="already exist"):
        convert_snmp_walk(_plan(source, output))


def test_installed_cli_is_dry_run_by_default_and_requires_execute(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "converted.snmprec"
    stdout = StringIO()
    common = (
        "snmp",
        "convert-walk",
        str(source),
        "--output",
        str(output),
        "--expected-sha256",
        hashlib.sha256(source.read_bytes()).hexdigest(),
        "--source-url",
        "https://example.invalid/authorized-fixture",
        "--license",
        "BSD-2-Clause",
        "--device-category",
        "switch",
        "--sanitized",
        "--approved-by",
        "lab.operator",
        "--approved-at",
        NOW.isoformat(),
        "--rationale",
        "Declared vendor dump as Net-SNMP walk text",
    )

    assert main(common, stdout=stdout, stderr=StringIO()) == 0
    assert json.loads(stdout.getvalue())["dry_run"] is True
    assert not output.exists()

    assert main((*common, "--execute"), stdout=StringIO(), stderr=StringIO()) == 0
    assert output.is_file()
