"""CLI boundary for controlled offline SNMP walk conversion."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TextIO

from twinforge.discovery import (
    SnmpConversionError,
    SnmpWalkConversionPlan,
    convert_snmp_walk,
    snmp_walk_conversion_plan_json,
)


def convert_walk_command(
    input_path: Path,
    output_path: Path,
    *,
    expected_sha256: str,
    source_url: str,
    license_name: str,
    device_category: str,
    sanitized: bool,
    approved_by: str,
    approved_at: str,
    rationale: str,
    max_input_bytes: int,
    allow_unparsed_lines: bool,
    execute: bool,
    stdout: TextIO,
) -> None:
    """Print a dry run or execute one attributable offline conversion."""
    try:
        approval_time = datetime.fromisoformat(approved_at)
    except ValueError as error:
        raise SnmpConversionError(
            "approved_at must be a timezone-qualified ISO 8601 timestamp"
        ) from error
    plan = SnmpWalkConversionPlan(
        input_path=input_path,
        output_path=output_path,
        expected_sha256=expected_sha256,
        source_url=source_url,
        license=license_name,
        device_category=device_category,
        sanitized=sanitized,
        approved_by=approved_by,
        approved_at=approval_time,
        rationale=rationale,
        max_input_bytes=max_input_bytes,
        allow_unparsed_lines=allow_unparsed_lines,
    )
    if not execute:
        stdout.write(snmp_walk_conversion_plan_json(plan))
        return
    receipt = convert_snmp_walk(plan)
    stdout.write(json.dumps(receipt.__dict__, indent=2) + "\n")
