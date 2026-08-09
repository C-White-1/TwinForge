import json

from twinforge.discovery.software_inventory_plan import (
    CipSoftwareInventoryCapability,
)
from twinforge.discovery.software_inventory_pycomm3 import (
    assess_pycomm3_software_inventory,
    pycomm3_software_inventory_assessment_json,
)


def test_verified_version_records_capabilities_but_refuses_live_compatibility() -> None:
    assessment = assess_pycomm3_software_inventory("1.2.16")
    document = json.loads(
        pycomm3_software_inventory_assessment_json(assessment)
    )

    assert assessment.discoverable_capabilities == (
        CipSoftwareInventoryCapability.PROGRAMS,
        CipSoftwareInventoryCapability.ROUTINES,
        CipSoftwareInventoryCapability.TAG_DEFINITIONS,
        CipSoftwareInventoryCapability.TASKS,
    )
    assert assessment.externally_budget_controllable is False
    assert assessment.live_executor_compatible is False
    assert "pagination internally" in str(document["limitation"])


def test_uninspected_version_claims_no_capabilities() -> None:
    assessment = assess_pycomm3_software_inventory("9.9.9")

    assert assessment.verified_version is False
    assert assessment.discoverable_capabilities == ()
    assert assessment.evidence_references == ()
