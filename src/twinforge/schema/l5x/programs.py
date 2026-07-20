from .spec import AttributeSpec, ElementSpec
from .tags import TAGS_ELEMENTS


PROGRAM_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name",
        description="Name of the program.",
        required=True,
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Program attributes.",
    ),
    "TestEdits": AttributeSpec(
        name="TestEdits",
        description="Indicates whether the program contains active test edits.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Program attributes.",
    ),
    "MainRoutineName": AttributeSpec(
        name="MainRoutineName",
        description="Name of the program's main routine.",
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Program attributes.",
    ),
    "Disabled": AttributeSpec(
        name="Disabled",
        description="Indicates whether execution of the program is disabled.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Program attributes.",
    ),
    "UseAsFolder": AttributeSpec(
        name="UseAsFolder",
        description="Indicates whether the program is used as an organizational folder.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Program attributes.",
    ),
    "PermissionSet": AttributeSpec(
        name="PermissionSet",
        description="FactoryTalk Security permission set applied to the program.",
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Program attributes.",
    ),
}


ROUTINE_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name",
        description="Name of the routine.",
        required=True,
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Routine attributes.",
    ),
    "Type": AttributeSpec(
        name="Type",
        description="Programming language used by the routine.",
        required=True,
        datatype=str,
        valid_values=("RLL", "ST", "SFC", "FBD"),
        manual_ref="1756-RM014D-EN-P September 2025, Routine attributes.",
    ),
}

RUNG_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Number": AttributeSpec(
        name="Number", description="Routine-local rung number.", required=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, RLL rung attributes.",
    ),
    "Type": AttributeSpec(
        name="Type", description="Rung state/type marker.", required=True,
        manual_ref="1756-RM014D-EN-P September 2025, RLL rung attributes.",
    ),
}

RUNG_ELEMENTS: dict[str, ElementSpec] = {
    "Comment": ElementSpec(
        name="Comment", description="User comment associated with the rung.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, RLL rung structure.",
    ),
    "Text": ElementSpec(
        name="Text", description="Logix instruction text for the rung.", required=True,
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, RLL rung structure.",
    ),
}

RLL_CONTENT_ELEMENTS: dict[str, ElementSpec] = {
    "Rung": ElementSpec(
        name="Rung", description="One relay ladder logic rung.",
        attributes=RUNG_ATTRIBUTES, elements=RUNG_ELEMENTS, repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, RLL routine structure.",
    ),
}

ROUTINE_ELEMENTS: dict[str, ElementSpec] = {
    "RLLContent": ElementSpec(
        name="RLLContent", description="Relay ladder logic content of an RLL routine.",
        elements=RLL_CONTENT_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, RLL routine structure.",
    ),
}


ROUTINES_ELEMENTS: dict[str, ElementSpec] = {
    "Routine": ElementSpec(
        name="Routine",
        description="A routine belonging to a program.",
        attributes=ROUTINE_ATTRIBUTES,
        elements=ROUTINE_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Program structure.",
    ),
}


PROGRAM_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description",
        description="User description of the program.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, Program structure.",
    ),
    "Tags": ElementSpec(
        name="Tags",
        description="Container for program-scoped tags.",
        elements=TAGS_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Program structure.",
    ),
    "Routines": ElementSpec(
        name="Routines",
        description="Container for routines belonging to the program.",
        elements=ROUTINES_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Program structure.",
    ),
}


PROGRAMS_ELEMENTS: dict[str, ElementSpec] = {
    "Program": ElementSpec(
        name="Program",
        description="A controller program.",
        attributes=PROGRAM_ATTRIBUTES,
        elements=PROGRAM_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Program structure.",
    ),
}
