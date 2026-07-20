from .spec import AttributeSpec, ElementSpec


DATATYPE_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name", description="Name of the controller-defined data type.",
        required=True, l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Data type attributes.",
    ),
    "Family": AttributeSpec(
        name="Family", description="Data type family classification.",
        manual_ref="1756-RM014D-EN-P September 2025, Data type attributes.",
    ),
    "Class": AttributeSpec(
        name="Class", description="Data type class classification.",
        manual_ref="1756-RM014D-EN-P September 2025, Data type attributes.",
    ),
}

DATATYPE_MEMBER_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name", description="Name of the data type member.", required=True,
        manual_ref="1756-RM014D-EN-P September 2025, Data type member attributes.",
    ),
    "DataType": AttributeSpec(
        name="DataType", description="Data type of the member.", required=True,
        manual_ref="1756-RM014D-EN-P September 2025, Data type member attributes.",
    ),
    "Dimension": AttributeSpec(
        name="Dimension", description="Array dimension of the member.",
        manual_ref="1756-RM014D-EN-P September 2025, Data type member attributes.",
    ),
    "Radix": AttributeSpec(
        name="Radix", description="Preferred display radix for the member.",
        manual_ref="1756-RM014D-EN-P September 2025, Data type member attributes.",
    ),
    "Hidden": AttributeSpec(
        name="Hidden", description="Indicates whether the member is hidden.",
        xml_type=str, datatype=bool, valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Data type member attributes.",
    ),
    "ExternalAccess": AttributeSpec(
        name="ExternalAccess", description="External access permitted for the member.",
        valid_values=("Read/Write", "Read Only", "None"),
        manual_ref="1756-RM014D-EN-P September 2025, Data type member attributes.",
    ),
}

DATATYPE_MEMBER_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description", description="User description of the member.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, Data type structure.",
    ),
}

DATATYPE_MEMBERS_ELEMENTS: dict[str, ElementSpec] = {
    "Member": ElementSpec(
        name="Member", description="A member of a controller-defined data type.",
        attributes=DATATYPE_MEMBER_ATTRIBUTES, elements=DATATYPE_MEMBER_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Data type structure.",
    ),
}

DATATYPE_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description", description="User description of the data type.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, Data type structure.",
    ),
    "Members": ElementSpec(
        name="Members", description="Members of the controller-defined data type.",
        elements=DATATYPE_MEMBERS_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Data type structure.",
    ),
}

DATATYPES_ELEMENTS: dict[str, ElementSpec] = {
    "DataType": ElementSpec(
        name="DataType", description="A controller-defined structured data type.",
        attributes=DATATYPE_ATTRIBUTES, elements=DATATYPE_ELEMENTS, repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Data type structure.",
    ),
}
