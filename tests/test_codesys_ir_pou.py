import xml.etree.ElementTree as ET

from twinforge.exporters.codesys_ir_pou import (
    CodesysIRInterfaceEmitter,
    CodesysIRPOUEmitter,
)
from twinforge.exporters.plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from twinforge.ir import (
    IRDirection,
    IRParameter,
    IRReusableUnit,
    IRUnitKind,
    IRVariable,
)


NS = {
    "p": PLCOPEN_CODESYS_NAMESPACE,
    "x": "http://www.w3.org/1999/xhtml",
}


def _unit(
    *,
    kind: IRUnitKind = IRUnitKind.FUNCTION_BLOCK,
    parameters: tuple[IRParameter, ...] = (),
    variables: tuple[IRVariable, ...] = (),
) -> IRReusableUnit:
    return IRReusableUnit(
        name="ReusableUnit",
        kind=kind,
        parameters=parameters,
        variables=variables,
        routines=(),
    )


def test_datatype_encoder_handles_arrays_strings_and_unresolved_types() -> None:
    emitter = CodesysIRInterfaceEmitter()
    root = ET.Element("types")

    emitter.data_type(root, "DINT", "3,1")
    emitter.data_type(root, "STRING(80)", None)
    emitter.data_type(root, "DriveStatus", None)
    emitter.data_type(root, None, None)

    dimensions = root.findall("p:array/p:dimension", NS)
    assert [item.attrib for item in dimensions] == [
        {"lower": "0", "upper": "2"},
        {"lower": "0", "upper": "0"},
    ]
    assert root.find("p:array/p:baseType/p:DINT", NS) is not None
    assert root.find("p:string[@length='80']", NS) is not None
    derived = root.findall("p:derived", NS)
    assert [item.attrib["name"] for item in derived] == [
        "DriveStatus",
        "TF_UNRESOLVED_TYPE",
    ]


def test_interface_groups_parameters_and_encodes_generic_array_evidence() -> None:
    interface = ET.Element(f"{{{PLCOPEN_CODESYS_NAMESPACE}}}interface")
    unit = _unit(
        parameters=(
            IRParameter("Enable", IRDirection.INPUT, "BOOL"),
            IRParameter("Done", IRDirection.OUTPUT, "BOOL"),
            IRParameter(
                "Data",
                IRDirection.INOUT,
                "SINT",
                dimensions="1,1",
                generic_dimensions=True,
            ),
        ),
        variables=(IRVariable("Count", "DINT"),),
    )

    CodesysIRInterfaceEmitter().emit(interface, unit)

    assert interface.find(
        "p:inputVars/p:variable[@name='Enable']/p:type/p:BOOL",
        NS,
    ) is not None
    assert interface.find(
        "p:outputVars/p:variable[@name='Done']/p:type/p:BOOL",
        NS,
    ) is not None
    assert interface.find(
        "p:localVars/p:variable[@name='Count']/p:type/p:DINT",
        NS,
    ) is not None
    generic = interface.find(
        "p:inputVars/p:variable[@name='Data']",
        NS,
    )
    assert generic is not None
    assert generic.find("p:type/p:pointer/p:baseType/p:SINT", NS) is not None
    attributes = {
        item.attrib["Name"]: item.attrib["Value"]
        for item in generic.findall(
            "p:addData/p:data/p:Attributes/p:Attribute",
            NS,
        )
    }
    assert attributes == {
        "variable_length_array_original_scope": "Inout",
        "variable_length_array": "ARRAY[*, *] OF SINT",
        "Dimensions": "2",
    }


def test_pou_emitter_delegates_body_lifecycle_and_identity() -> None:
    parent = ET.Element("wrapper")
    calls: list[tuple[str, str]] = []

    def lifecycle(add_data: ET.Element, unit: IRReusableUnit) -> None:
        calls.append(("lifecycle", unit.name))
        ET.SubElement(add_data, "Lifecycle")

    def append_identity(add_data: ET.Element, object_id: str) -> None:
        calls.append(("identity", object_id))
        ET.SubElement(add_data, "ObjectId").text = object_id

    CodesysIRPOUEmitter(
        interface_emitter=CodesysIRInterfaceEmitter(),
        body_text=lambda unit: f"{unit.name} body",
        emit_lifecycle=lifecycle,
        object_id=lambda path: f"id:{path}",
        append_object_id=append_identity,
    ).emit(parent, _unit(kind=IRUnitKind.FUNCTION))

    pou = parent.find("p:pou[@name='ReusableUnit']", NS)
    assert pou is not None and pou.attrib["pouType"] == "function"
    assert (
        pou.findtext("p:body/p:ST/x:xhtml", namespaces=NS)
        == "ReusableUnit body"
    )
    assert calls == [
        ("lifecycle", "ReusableUnit"),
        ("identity", "id:Application/pou/ReusableUnit"),
    ]
    assert pou.find("p:addData/Lifecycle", NS) is not None
    assert (
        pou.findtext("p:addData/ObjectId", namespaces=NS)
        == "id:Application/pou/ReusableUnit"
    )
