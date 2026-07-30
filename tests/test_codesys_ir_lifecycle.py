import xml.etree.ElementTree as ET

import pytest

from twinforge.exporters.codesys_ir_lifecycle import (
    CodesysIRLifecycleEmitter,
)
from twinforge.exporters.plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from twinforge.ir import (
    IRLifecycle,
    IRReusableUnit,
    IRRoutine,
    IRRoutineRole,
    IRUnitKind,
)


NS = {
    "p": PLCOPEN_CODESYS_NAMESPACE,
    "x": "http://www.w3.org/1999/xhtml",
}


def _unit(
    *,
    kind: IRUnitKind = IRUnitKind.FUNCTION_BLOCK,
    prescan_enabled: bool | None = True,
    include_prescan: bool = True,
) -> IRReusableUnit:
    routines = (
        (
            IRRoutine(
                name="Prescan",
                source_language="ST",
                source="",
                statements=(),
                role=IRRoutineRole.PRESCAN,
            ),
        )
        if include_prescan
        else ()
    )
    return IRReusableUnit(
        name="LifecycleUnit",
        kind=kind,
        parameters=(),
        variables=(),
        routines=routines,
        lifecycle=IRLifecycle(prescan_enabled=prescan_enabled),
    )


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        (_unit(), True),
        (_unit(prescan_enabled=False), False),
        (_unit(prescan_enabled=None), False),
        (_unit(kind=IRUnitKind.FUNCTION), False),
        (_unit(include_prescan=False), False),
    ],
)
def test_prescan_mapping_requires_enabled_function_block_routine(
    unit: IRReusableUnit,
    expected: bool,
) -> None:
    emitter = CodesysIRLifecycleEmitter(object_id=lambda path: path)

    assert emitter.has_mapped_prescan(unit) is expected


def test_fb_init_method_shape_and_identity_are_deterministic() -> None:
    emitter = CodesysIRLifecycleEmitter(
        object_id=lambda path: f"id:{path}"
    )
    add_data = ET.Element(f"{{{PLCOPEN_CODESYS_NAMESPACE}}}addData")
    unit = _unit()

    emitter.emit(add_data, unit)

    method = add_data.find(
        "p:data[@name='http://www.3s-software.com/plcopenxml/method']/"
        "p:Method[@name='FB_Init']",
        NS,
    )
    assert method is not None
    assert method.attrib["ObjectId"] == (
        "id:Application/pou/LifecycleUnit/method/FB_Init"
    )
    assert method.find("p:interface/p:returnType/p:BOOL", NS) is not None
    assert [
        variable.attrib["name"]
        for variable in method.findall(
            "p:interface/p:inputVars/p:variable",
            NS,
        )
    ] == ["bInitRetains", "bInCopyCode"]
    assert (
        method.findtext("p:body/p:ST/x:xhtml", namespaces=NS)
        == "\nFB_Init := TRUE;"
    )
    assert method.find("p:addData", NS) is not None


def test_ineligible_unit_emits_no_method() -> None:
    emitter = CodesysIRLifecycleEmitter(object_id=lambda path: path)
    add_data = ET.Element(f"{{{PLCOPEN_CODESYS_NAMESPACE}}}addData")

    emitter.emit(add_data, _unit(prescan_enabled=False))

    assert list(add_data) == []
