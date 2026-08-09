from datetime import datetime, timezone

from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.software_inventory_capture import (
    CipSoftwareInventoryItem,
    CipSoftwareInventoryObservation,
)
from twinforge.discovery.software_inventory_plan import (
    CipSoftwareInventoryCapability,
)
from twinforge.discovery.software_inventory_reconciliation import (
    SoftwareInventoryComparison,
    SoftwareInventoryComparisonStatus,
    SoftwareInventoryReconciliationResult,
)
from twinforge.discovery.software_inventory_report import (
    software_inventory_markdown,
)


def test_default_report_omits_raw_attributes_payloads_and_value_like_data() -> None:
    observation = CipSoftwareInventoryObservation(
        target=DiscoveryTarget(address="192.168.1.10"),
        engagement="TwinForge controlled lab",
        authorization_reference="LAB-001",
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        capabilities=(CipSoftwareInventoryCapability.TAG_DEFINITIONS,),
        requests_used=1,
        items=(
            CipSoftwareInventoryItem(
                capability=CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                name="MotorRun",
                data_type="BOOL",
                raw_attributes={
                    "value": "DO-NOT-REPORT",
                    "vendor_blob": "SECRET-PAYLOAD",
                },
            ),
        ),
    )
    reconciliation = SoftwareInventoryReconciliationResult(
        binding_key="L5X:Controller",
        comparisons=(
            SoftwareInventoryComparison(
                key="tag_definitions|controller|MotorRun",
                status=SoftwareInventoryComparisonStatus.EXACT,
                matched_fields=("name", "data_type"),
                conflicting_fields=(),
                unavailable_fields=(),
            ),
        ),
        configured_only=(),
        discovered_only=(),
    )

    report = software_inventory_markdown(observation, reconciliation)

    assert "MotorRun" in report
    assert "data type `BOOL`" in report
    assert "Runtime values included: no" in report
    assert "DO-NOT-REPORT" not in report
    assert "SECRET-PAYLOAD" not in report
    assert "raw_attributes" not in report
