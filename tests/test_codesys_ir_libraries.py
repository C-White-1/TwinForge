import xml.etree.ElementTree as ET

from twinforge.exporters.codesys_ir_libraries import CodesysIRLibraryEmitter
from twinforge.exporters.plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from twinforge.ir import IRReusableUnit, IRUnitKind, IRVariable


NS = {"p": PLCOPEN_CODESYS_NAMESPACE}


def _unit(*data_types: str) -> IRReusableUnit:
    return IRReusableUnit(
        name="Unit",
        kind=IRUnitKind.FUNCTION_BLOCK,
        parameters=(),
        variables=tuple(
            IRVariable(f"Value{index}", data_type)
            for index, data_type in enumerate(data_types)
        ),
        routines=(),
    )


def _emitter(
    identities: list[str],
) -> CodesysIRLibraryEmitter:
    def append_identity(parent: ET.Element, object_id: str) -> None:
        identities.append(object_id)
        ET.SubElement(parent, "ObjectId").text = object_id

    return CodesysIRLibraryEmitter(
        object_id=lambda path: f"id:{path}",
        append_object_id=append_identity,
    )


def test_required_detects_supported_wall_clock_runtime_types() -> None:
    assert not CodesysIRLibraryEmitter.required([_unit("BOOL", "DINT")])
    assert CodesysIRLibraryEmitter.required([_unit("SysTime")])
    assert CodesysIRLibraryEmitter.required(
        [_unit("BOOL"), _unit("SysTypes.RTS_IEC_RESULT")]
    )


def test_emit_writes_proven_library_metadata_and_identity() -> None:
    identities: list[str] = []
    emitter = _emitter(identities)
    parent = ET.Element("addData")

    assert emitter.emit(parent, [_unit("SysTime")])

    libraries = parent.findall(
        "p:data[@name='http://www.3s-software.com/plcopenxml/libraries']/"
        "p:Libraries/p:Library",
        NS,
    )
    assert [item.attrib["Name"] for item in libraries] == [
        "#SysTimeRtc",
        "SysTime, 3.5.17.0 (System)",
        "SysTypes2 Interfaces, * (System)",
    ]
    assert [item.attrib["Namespace"] for item in libraries] == [
        "SysTimeRtc",
        "SysTime",
        "SysTypes",
    ]
    assert all(
        item.attrib["HideWhenReferencedAsDependency"] == "false"
        and item.attrib["LinkAllContent"] == "false"
        for item in libraries
    )
    assert identities == ["id:Application/Library Manager"]


def test_resource_and_project_tree_omit_unneeded_library_manager() -> None:
    identities: list[str] = []
    emitter = _emitter(identities)
    resource = ET.Element("addData")
    application = ET.Element(
        f"{{{PLCOPEN_CODESYS_NAMESPACE}}}Object"
    )
    units = [_unit("BOOL")]

    assert not emitter.emit(resource, units)
    assert not emitter.append_project_object(application, units)

    assert list(resource) == []
    assert list(application) == []
    assert identities == []


def test_project_tree_uses_same_library_manager_identity() -> None:
    identities: list[str] = []
    emitter = _emitter(identities)
    application = ET.Element(
        f"{{{PLCOPEN_CODESYS_NAMESPACE}}}Object"
    )

    assert emitter.append_project_object(application, [_unit("SysTime")])

    manager = application.find("p:Object[@Name='Library Manager']", NS)
    assert manager is not None
    assert manager.attrib["ObjectId"] == "id:Application/Library Manager"
