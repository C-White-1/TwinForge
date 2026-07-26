"""Specification fragments for L5X Add-On Instruction definitions."""

from .programs import ROUTINES_ELEMENTS
from .spec import AttributeSpec, ElementSpec


BOOLEAN = ("true", "false")

AOI_ATTRIBUTES = {
    "Use": AttributeSpec(
        name="Use", description="Context or target role in the export.",
        valid_values=("Context", "Target")
    ),
    "Name": AttributeSpec(
        name="Name", description="Instruction definition name.", required=True
    ),
    "Revision": AttributeSpec(
        name="Revision", description="Instruction definition revision."
    ),
    "Vendor": AttributeSpec(
        name="Vendor", description="Instruction definition vendor."
    ),
    "ExecutePrescan": AttributeSpec(
        name="ExecutePrescan", description="Whether prescan logic executes.",
        datatype=bool, valid_values=BOOLEAN
    ),
    "ExecutePostscan": AttributeSpec(
        name="ExecutePostscan", description="Whether postscan logic executes.",
        datatype=bool, valid_values=BOOLEAN
    ),
    "ExecuteEnableInFalse": AttributeSpec(
        name="ExecuteEnableInFalse",
        description="Whether EnableInFalse logic executes.",
        datatype=bool, valid_values=BOOLEAN
    ),
    "CreatedDate": AttributeSpec(
        name="CreatedDate", description="Definition creation timestamp."
    ),
    "CreatedBy": AttributeSpec(
        name="CreatedBy", description="Definition creator."
    ),
    "EditedDate": AttributeSpec(
        name="EditedDate", description="Last edit timestamp."
    ),
    "EditedBy": AttributeSpec(
        name="EditedBy", description="Last editor."
    ),
    "SoftwareRevision": AttributeSpec(
        name="SoftwareRevision", description="Creating software revision."
    ),
}

PARAMETER_ATTRIBUTES = {
    "Name": AttributeSpec(
        name="Name", description="Parameter name.", required=True
    ),
    "TagType": AttributeSpec(
        name="TagType", description="Parameter storage category."
    ),
    "DataType": AttributeSpec(
        name="DataType", description="Parameter data type.", required=True
    ),
    "Dimensions": AttributeSpec(
        name="Dimensions", description="Parameter array dimensions."
    ),
    "Usage": AttributeSpec(
        name="Usage", description="Parameter data-flow direction.",
        required=True, valid_values=("Input", "Output", "InOut")
    ),
    "Radix": AttributeSpec(
        name="Radix", description="Preferred display radix."
    ),
    "Required": AttributeSpec(
        name="Required", description="Whether an argument is required.",
        datatype=bool, valid_values=BOOLEAN
    ),
    "Visible": AttributeSpec(
        name="Visible", description="Whether the parameter is visible.",
        datatype=bool, valid_values=BOOLEAN
    ),
    "Constant": AttributeSpec(
        name="Constant", description="Whether the parameter is constant.",
        datatype=bool, valid_values=BOOLEAN
    ),
    "ExternalAccess": AttributeSpec(
        name="ExternalAccess",
        description="External access permitted for the parameter.",
        valid_values=("Read/Write", "Read Only", "None"),
    ),
    "AliasFor": AttributeSpec(
        name="AliasFor",
        description="Local member referenced by an alias parameter.",
    ),
}

DEFAULT_DATA_ATTRIBUTES = {
    "Format": AttributeSpec(
        name="Format",
        description="Serialization format for the default value.",
        required=True,
        valid_values=("L5K", "Decorated", "String"),
    )
}

PARAMETER_ELEMENTS = {
    "Description": ElementSpec(
        name="Description", content_type="cdata"
    ),
    "DefaultData": ElementSpec(
        name="DefaultData",
        attributes=DEFAULT_DATA_ATTRIBUTES,
        content_type="mixed",
        repeatable=True,
    ),
}

LOCAL_TAG_ATTRIBUTES = {
    "Name": AttributeSpec(
        name="Name", description="AOI-local tag name.", required=True
    ),
    "DataType": AttributeSpec(
        name="DataType", description="AOI-local tag data type.",
        required=True,
    ),
    "Dimensions": AttributeSpec(
        name="Dimensions", description="AOI-local tag array dimensions."
    ),
    "Radix": AttributeSpec(
        name="Radix", description="Preferred display radix."
    ),
    "ExternalAccess": AttributeSpec(
        name="ExternalAccess",
        description="External access permitted for the local tag.",
        valid_values=("Read/Write", "Read Only", "None"),
    ),
}

LOCAL_TAG_ELEMENTS = {
    "Description": ElementSpec(
        name="Description", content_type="cdata"
    ),
    "DefaultData": ElementSpec(
        name="DefaultData",
        attributes=DEFAULT_DATA_ATTRIBUTES,
        content_type="mixed",
        repeatable=True,
    ),
}

DEPENDENCY_ATTRIBUTES = {
    "Type": AttributeSpec(
        name="Type", description="Kind of referenced definition.",
        required=True,
    ),
    "Name": AttributeSpec(
        name="Name", description="Name of referenced definition.",
        required=True,
    ),
}

AOI_ELEMENTS = {
    "Description": ElementSpec(
        name="Description", content_type="cdata"
    ),
    "Parameters": ElementSpec(
        name="Parameters",
        elements={
            "Parameter": ElementSpec(
                name="Parameter",
                attributes=PARAMETER_ATTRIBUTES,
                elements=PARAMETER_ELEMENTS,
                repeatable=True,
            )
        },
    ),
    "LocalTags": ElementSpec(
        name="LocalTags",
        elements={
            "LocalTag": ElementSpec(
                name="LocalTag",
                attributes=LOCAL_TAG_ATTRIBUTES,
                elements=LOCAL_TAG_ELEMENTS,
                repeatable=True,
            )
        },
    ),
    "Routines": ElementSpec(
        name="Routines", elements=ROUTINES_ELEMENTS
    ),
    "AdditionalHelpText": ElementSpec(
        name="AdditionalHelpText", content_type="cdata"
    ),
    "Dependencies": ElementSpec(
        name="Dependencies",
        elements={
            "Dependency": ElementSpec(
                name="Dependency",
                attributes=DEPENDENCY_ATTRIBUTES,
                repeatable=True,
            )
        },
    ),
}

ADD_ON_INSTRUCTION_ELEMENTS = {
    "AddOnInstructionDefinition": ElementSpec(
        name="AddOnInstructionDefinition",
        attributes=AOI_ATTRIBUTES,
        elements=AOI_ELEMENTS,
        repeatable=True,
    )
}
