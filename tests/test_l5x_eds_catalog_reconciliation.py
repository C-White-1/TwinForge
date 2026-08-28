"""Controller-level EDS catalogue reconciliation tests."""

from pathlib import Path

from twinforge.analysis.eds_catalog_reconciliation import (
    ModuleCatalogStatus,
    assess_controller_eds_catalog,
)
from twinforge.knowledge.device_catalog import DeviceCatalogRecord
from twinforge.model import (
    Chassis,
    Controller,
    ElectronicKey,
    Identity,
    KeyingMode,
    Module,
    Revision,
    VendorIdentity,
)


def _identity(revision: int) -> Identity:
    return Identity(
        vendor=VendorIdentity(1),
        product_type=7,
        product_code=11,
        revision=Revision(revision, 1),
    )


class _Catalog:
    def find_by_catalog_number(
        self,
        catalog_number: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        return self.find_by_base_catalog_number(catalog_number)

    def find_by_base_catalog_number(
        self,
        catalog_number: str,
    ) -> tuple[DeviceCatalogRecord, ...]:
        if catalog_number != "1756-IB16":
            return ()
        return (
            DeviceCatalogRecord(
                source_key="2.1",
                source_file=Path("revision-2.eds"),
                catalog_number="1756-IB16/A",
                identity=_identity(2),
            ),
            DeviceCatalogRecord(
                source_key="3.1",
                source_file=Path("revision-3.eds"),
                catalog_number="1756-IB16/A",
                identity=_identity(3),
            ),
        )


def test_assesses_controller_modules_and_retains_compatible_ambiguity() -> None:
    controller = Controller(name="Controller", identity=Identity())
    chassis = Chassis(name="Local")
    chassis.add_module(
        Module(
            name="DI_Slot1",
            catalog="1756-IB16",
            slot=1,
            identity=_identity(3),
            electronic_key=ElectronicKey(mode=KeyingMode.COMPATIBLE_MODULE),
        )
    )
    controller.add_chassis(chassis)

    assessments = assess_controller_eds_catalog(controller, _Catalog())

    assert len(assessments) == 1
    assert assessments[0].status is ModuleCatalogStatus.ADVISORY
    assert assessments[0].reconciliation.selected is None
    assert len(assessments[0].reconciliation.candidates) == 2
