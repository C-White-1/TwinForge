"""Declarative selectors for the observed basic neutral mapping profile.

Paths are relative child names, not namespace-stripping XPath expressions.
New vendor layouts require evidence and an explicit profile entry.
"""
from dataclasses import dataclass

PathSpec = tuple[str, ...]


@dataclass(frozen=True)
class HardwareLayout:
    racks: PathSpec
    modules: tuple[str, ...]


@dataclass(frozen=True)
class MappingSpec:
    # READ_VAR GEST is emitted as separate input/output pins for one inout parameter.
    library_direction_aliases: tuple[tuple[str, str], ...] = (("inout", "input"), ("inout", "output"))
    library_definitions: tuple[tuple[str, str, str], ...] = (
        ("EFBSource", "nameOfEFBType", "function_block"),
        ("EFSource", "nameOfEFType", "function"),
    )
    library_parameters: tuple[tuple[PathSpec, str], ...] = (
        (("ExternalToolsOnly", "inputParameters", "variables"), "input"),
        (("ExternalToolsOnly", "outputParameters", "variables"), "output"),
        (("ExternalToolsOnly", "inOutParameters", "variables"), "inout"),
    )
    roots: tuple[str, ...] = ("FEFExchangeFile", "ZEFExchangeFile")
    header: PathSpec = ("fileHeader",)
    content: PathSpec = ("contentHeader",)
    variables: PathSpec = ("dataBlock", "variables")
    tasks: PathSpec = ("logicConf", "resource", "taskDesc")
    sections: PathSpec = ("program",)
    additional_sections: tuple[PathSpec, ...] = (("SFCProgram",),)
    section_identity: PathSpec = ("identProgram",)
    task_sections: PathSpec = ("sectionDesc",)
    comments: PathSpec = ("comment",)
    initializers: PathSpec = ("variableInit",)
    plc: PathSpec = ("IOConf", "PLC")
    part: PathSpec = ("partItem",)
    equipment: PathSpec = ("equipInfo",)
    languages: tuple[tuple[str, str], ...] = (
        ("chartSource", "SFC"), ("STSource", "ST"), ("LDSource", "LD"), ("FBDSource", "FBD"),
    )
    hardware_layouts: tuple[HardwareLayout, ...] = (
        HardwareLayout(
            ("configQuantum", "IOMapBlock", "busQuantum", "dropQuantum", "rackQuantum"),
            ("moduleQuantum",),
        ),
        HardwareLayout(("configATS", "busATS", "rackATS"), ("moduleATS", "powerSupply")),
    )
    scalar_types: frozenset[str] = frozenset({
        "BOOL", "INT", "DINT", "WORD", "TIME", "STRING",
    })
    array_pattern: str = r"ARRAY\[(-?\d+)\.\.(-?\d+)\] OF ([A-Za-z_][A-Za-z_0-9]*)"


BASIC_MAPPING = MappingSpec()
