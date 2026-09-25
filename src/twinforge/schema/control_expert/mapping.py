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
    # A power supply mounts separately from the numbered slot scheme; its own
    # tag(s), if any are evidenced for this layout, keep it out of `modules`.
    power_supply_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class MappingSpec:
    # READ_VAR GEST is emitted as separate input/output pins for one inout parameter.
    library_direction_aliases: tuple[tuple[str, str], ...] = (("inout", "input"), ("inout", "output"))
    library_definitions: tuple[tuple[str, str, str], ...] = (
        ("EFBSource", "nameOfEFBType", "function_block"),
        ("EFSource", "nameOfEFType", "function"),
        ("FBSource", "nameOfFBType", "user_function_block"),
    )
    library_parameters: tuple[tuple[PathSpec, str], ...] = (
        (("ExternalToolsOnly", "inputParameters", "variables"), "input"),
        (("ExternalToolsOnly", "outputParameters", "variables"), "output"),
        (("ExternalToolsOnly", "inOutParameters", "variables"), "inout"),
        # FBSource declares the identical shape directly (not nested under
        # ExternalToolsOnly) whenever its implementation body is not crypted;
        # the two locations are mutually exclusive per definition, observed.
        (("inputParameters", "variables"), "input"),
        (("outputParameters", "variables"), "output"),
        (("inOutParameters", "variables"), "inout"),
    )
    function_blocks: PathSpec = ("FBSource",)
    function_block_name_attribute: str = "nameOfFBType"
    function_block_program: PathSpec = ("FBProgram",)
    function_block_crypted: PathSpec = ("crypted",)
    function_block_public_locals: PathSpec = ("publicLocalVariables", "variables")
    function_block_private_locals: PathSpec = ("privateLocalVariables", "variables")
    roots: tuple[str, ...] = ("FEFExchangeFile", "ZEFExchangeFile")
    # A standalone Derived Function Block export (.xdb/.XDB): one FBSource at
    # the document root, not embedded inside a project. Deliberately a
    # separate set from `roots` -- an .xdb is not a project (no tags,
    # hardware, programs), so parse_function_block_library never accepts one
    # of these roots and parse_project never accepts an FBExchangeFile.
    function_block_library_roots: tuple[str, ...] = ("FBExchangeFile",)
    header: PathSpec = ("fileHeader",)
    content: PathSpec = ("contentHeader",)
    variables: PathSpec = ("dataBlock", "variables")
    tasks: PathSpec = ("logicConf", "resource", "taskDesc")
    sections: PathSpec = ("program",)
    additional_sections: tuple[PathSpec, ...] = (("SFCProgram",),)
    section_identity: PathSpec = ("identProgram",)
    resources: PathSpec = ("logicConf", "resource")
    resource_name_attribute: str = "resName"
    resource_identifier_attribute: str = "resIdent"
    resource_tasks: PathSpec = ("taskDesc",)
    # Variables declared inside a resource, visible to that resource's programs only.
    resource_variables: tuple[PathSpec, ...] = (
        ("inputParameters", "variables"), ("outputParameters", "variables"),
        ("inOutParameters", "variables"), ("publicLocalVariables", "variables"),
        ("privateLocalVariables", "variables"),
    )
    task_sections: PathSpec = ("sectionDesc",)
    section_activation_attribute: str = "activationCondition"
    section_logic_attribute: str = "logicCondition"
    comments: PathSpec = ("comment",)
    initializers: PathSpec = ("variableInit",)
    instance_elements: PathSpec = ("instanceElementDesc",)
    datatypes: PathSpec = ("DDTSource",)
    datatype_name_attribute: str = "DDTName"
    datatype_members: PathSpec = ("structure", "variables")
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
        HardwareLayout(("configATS", "busATS", "rackATS"), ("moduleATS",),
                       power_supply_modules=("powerSupply",)),
    )
    scalar_types: frozenset[str] = frozenset({
        "BOOL", "INT", "DINT", "WORD", "TIME", "STRING",
        # Evidenced in the M580 safety corpus's DDT member declarations.
        # EBOOL is Schneider's own extended-BOOL elementary type (adds
        # rising/falling-edge and forcing), still scalar, not composite.
        "BYTE", "REAL", "EBOOL", "DWORD", "UDINT", "UINT",
        # Evidenced in the same corpus's DFB local-variable declarations
        # (TOD/DATE/DT abbreviate IEC 61131-3 TIME_OF_DAY/DATE/DATE_AND_TIME);
        # a genuinely elementary, unambiguous scalar family, not composite or
        # vendor-specific, the same reasoning the types above already apply.
        "TOD", "DATE", "DT",
    })
    array_pattern: str = r"ARRAY\[(-?\d+)\.\.(-?\d+)\] OF ([A-Za-z_][A-Za-z_0-9]*)"


BASIC_MAPPING = MappingSpec()
