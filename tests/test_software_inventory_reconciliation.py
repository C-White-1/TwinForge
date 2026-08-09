import json
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
    ConfiguredSoftwareBinding,
    SoftwareInventoryComparisonStatus,
    reconcile_software_inventory,
    software_inventory_reconciliation_json,
)
from twinforge.model import Controller, Identity, Program, Routine, Tag, Task


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _controller() -> Controller:
    controller = Controller(name="Configured", identity=Identity())
    program = Program(name="MainProgram")
    program.add_routine(Routine(name="MainRoutine", language="RLL"))
    program.add_tag(Tag(name="ProgramState", data_type="DINT"))
    controller.add_program(program)
    controller.add_task(Task(name="MainTask"))
    controller.add_tag(Tag(name="MotorRun", data_type="BOOL"))
    return controller


def test_reconciliation_reports_matches_conflicts_and_each_side_only() -> None:
    capabilities = (
        CipSoftwareInventoryCapability.PROGRAMS,
        CipSoftwareInventoryCapability.ROUTINES,
        CipSoftwareInventoryCapability.TAG_DEFINITIONS,
        CipSoftwareInventoryCapability.TASKS,
    )
    observation = CipSoftwareInventoryObservation(
        target=DiscoveryTarget(address="192.168.1.10"),
        captured_at=TIMESTAMP,
        capabilities=capabilities,
        requests_used=4,
        items=(
            CipSoftwareInventoryItem(
                CipSoftwareInventoryCapability.PROGRAMS,
                "MainProgram",
            ),
            CipSoftwareInventoryItem(
                CipSoftwareInventoryCapability.ROUTINES,
                "MainRoutine",
                parent="MainProgram",
                language="ST",
            ),
            CipSoftwareInventoryItem(
                CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                "MotorRun",
                data_type="BOOL",
            ),
            CipSoftwareInventoryItem(
                CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                "OnlineOnly",
                data_type="DINT",
            ),
        ),
    )

    result = reconcile_software_inventory(
        observation,
        ConfiguredSoftwareBinding("L5X:Configured", _controller()),
    )
    document = json.loads(software_inventory_reconciliation_json(result))

    statuses = {item.key: item.status for item in result.comparisons}
    assert statuses["programs|controller|MainProgram"] is (
        SoftwareInventoryComparisonStatus.EXACT
    )
    assert statuses["routines|MainProgram|MainRoutine"] is (
        SoftwareInventoryComparisonStatus.CONFLICT
    )
    assert "tag_definitions|controller|OnlineOnly" in result.discovered_only
    assert "tag_definitions|MainProgram|ProgramState" in result.configured_only
    assert "tasks|controller|MainTask" in result.configured_only
    assert document["runtime_values_included"] is False


def test_unrequested_capabilities_do_not_create_configured_only_noise() -> None:
    observation = CipSoftwareInventoryObservation(
        target=DiscoveryTarget(address="192.168.1.10"),
        captured_at=TIMESTAMP,
        capabilities=(CipSoftwareInventoryCapability.PROGRAMS,),
        requests_used=1,
        items=(),
    )

    result = reconcile_software_inventory(
        observation,
        ConfiguredSoftwareBinding("L5X:Configured", _controller()),
    )

    assert result.configured_only == ("programs|controller|MainProgram",)
