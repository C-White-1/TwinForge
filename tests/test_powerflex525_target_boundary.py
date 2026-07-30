import ast
from datetime import datetime, timezone
import hashlib
import inspect

from twinforge.exporters import (
    CodesysIRPLCopenExporter,
    PowerFlex525CodesysDevice as PublicDevice,
    build_codesys_sys_module_binding_unit,
    build_powerflex525_iec_unit,
)
from twinforge.exporters import powerflex525_iec as legacy
from twinforge.exporters import powerflex525_core
from twinforge.targets.codesys import (
    PowerFlex525CodesysDevice,
    powerflex525_codesys_application_integration,
    powerflex525_codesys_multi_application_integration,
)


FIXED_TIME = datetime(2026, 7, 27, tzinfo=timezone.utc)


def _export(integration, project_name: str) -> str:
    return CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        additional_units=(build_codesys_sys_module_binding_unit(),),
        project_name=project_name,
        creation_time=FIXED_TIME,
        integration=integration,
    ).xml


def test_neutral_powerflex_core_has_no_codesys_dependency() -> None:
    source = inspect.getsource(powerflex525_core)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert not any(
        "codesys" in module.casefold() or ".targets" in module
        for module in imports
    )


def test_public_and_legacy_device_types_are_target_compatibility_aliases() -> None:
    assert PublicDevice is PowerFlex525CodesysDevice
    assert legacy.PowerFlex525CodesysDevice is PowerFlex525CodesysDevice
    assert (
        legacy.powerflex525_codesys_application_integration
        is powerflex525_codesys_application_integration
    )


def test_single_and_multi_drive_documents_remain_byte_stable() -> None:
    single = _export(
        powerflex525_codesys_application_integration("Dev_Drive01"),
        "PowerFlexApplication",
    )
    multiple = _export(
        powerflex525_codesys_multi_application_integration(
            (
                PowerFlex525CodesysDevice("PF525_01", "Dev_PF525_01"),
                PowerFlex525CodesysDevice("PF525_02", "Dev_PF525_02"),
            )
        ),
        "TwoPowerFlexDrives",
    )

    assert hashlib.sha256(single.encode("utf-8")).hexdigest() == (
        "ee8415b810d9588fc8f7d605d3554640b60136404ce446357c58f7ceecd41d45"
    )
    assert hashlib.sha256(multiple.encode("utf-8")).hexdigest() == (
        "f1ac21e18afa2149a9a8794f6958ee26bcfc25c77261844999bdf1ae69c6b449"
    )
