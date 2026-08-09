"""Versioned assessment of pycomm3 structural inventory capabilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

from .software_inventory_plan import CipSoftwareInventoryCapability


@dataclass(frozen=True)
class Pycomm3SoftwareInventoryAssessment:
    """Evidence-based compatibility assessment without controller I/O."""

    library_version: str
    verified_version: bool
    discoverable_capabilities: tuple[CipSoftwareInventoryCapability, ...]
    externally_budget_controllable: bool
    live_executor_compatible: bool
    evidence_references: tuple[str, ...]
    limitation: str | None = None


def assess_pycomm3_software_inventory(
    library_version: str | None = None,
) -> Pycomm3SoftwareInventoryAssessment:
    """Assess only locally inspected pycomm3 versions conservatively."""
    detected = library_version or version("pycomm3")
    if detected != "1.2.16":
        return Pycomm3SoftwareInventoryAssessment(
            library_version=detected,
            verified_version=False,
            discoverable_capabilities=(),
            externally_budget_controllable=False,
            live_executor_compatible=False,
            evidence_references=(),
            limitation="pycomm3 version has not been inspected by TwinForge",
        )
    return Pycomm3SoftwareInventoryAssessment(
        library_version=detected,
        verified_version=True,
        discoverable_capabilities=(
            CipSoftwareInventoryCapability.PROGRAMS,
            CipSoftwareInventoryCapability.ROUTINES,
            CipSoftwareInventoryCapability.TAG_DEFINITIONS,
            CipSoftwareInventoryCapability.TASKS,
        ),
        externally_budget_controllable=False,
        live_executor_compatible=False,
        evidence_references=(
            "pycomm3.LogixDriver.get_tag_list",
            "pycomm3.LogixDriver._get_instance_attribute_list_service",
            "pycomm3.LogixDriver._isolate_user_tags",
        ),
        limitation=(
            "the public get_tag_list API performs pagination internally, so "
            "TwinForge cannot enforce its budget before every request"
        ),
    )


def pycomm3_software_inventory_assessment_data(
    assessment: Pycomm3SoftwareInventoryAssessment,
) -> dict[str, Any]:
    """Return deterministic, machine-readable assessment evidence."""
    return {
        "library": "pycomm3",
        "library_version": assessment.library_version,
        "verified_version": assessment.verified_version,
        "discoverable_capabilities": [
            item.value for item in assessment.discoverable_capabilities
        ],
        "externally_budget_controllable": (
            assessment.externally_budget_controllable
        ),
        "live_executor_compatible": assessment.live_executor_compatible,
        "evidence_references": list(assessment.evidence_references),
        "limitation": assessment.limitation,
    }


def pycomm3_software_inventory_assessment_json(
    assessment: Pycomm3SoftwareInventoryAssessment,
) -> str:
    """Serialize the adapter assessment deterministically."""
    return json.dumps(
        pycomm3_software_inventory_assessment_data(assessment),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
