from .spec import AttributeSpec, ElementSpec


TAG_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name",
        description="Name of the tag.",
        required=True,
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "TagType": AttributeSpec(
        name="TagType",
        description="Indicates whether the tag is a base tag or alias.",
        required=True,
        valid_values=("Base", "Alias"),
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "DataType": AttributeSpec(
        name="DataType",
        description="Data type of a base tag.",
        applicable_when=(("TagType", ("Base",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "Dimensions": AttributeSpec(
        name="Dimensions",
        description="Array dimensions of the tag.",
        applicable_when=(("TagType", ("Base",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "Radix": AttributeSpec(
        name="Radix",
        description="Preferred display radix for the tag value.",
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "Constant": AttributeSpec(
        name="Constant",
        description="Indicates whether the tag value is constant.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        applicable_when=(("TagType", ("Base",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "AliasFor": AttributeSpec(
        name="AliasFor",
        description="Target operand referenced by an alias tag.",
        applicable_when=(("TagType", ("Alias",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "ExternalAccess": AttributeSpec(
        name="ExternalAccess",
        description="External read/write access permitted for the tag.",
        valid_values=("Read/Write", "Read Only", "None"),
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
    "PermissionSet": AttributeSpec(
        name="PermissionSet",
        description="FactoryTalk Security permission set applied to the tag.",
        manual_ref="1756-RM014D-EN-P September 2025, Tag attributes.",
    ),
}


TAG_DATA_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Format": AttributeSpec(
        name="Format",
        description="Serialization format of the enclosed tag data.",
        required=True,
        valid_values=("L5K", "Decorated", "String", "Alarm"),
        manual_ref="1756-RM014D-EN-P September 2025, Tag data structure.",
    ),
}


TAG_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description",
        description="User description of the tag.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, Tag structure.",
    ),
    "Data": ElementSpec(
        name="Data",
        description="One serialized representation of the tag value.",
        attributes=TAG_DATA_ATTRIBUTES,
        repeatable=True,
        content_type="mixed",
        manual_ref="1756-RM014D-EN-P September 2025, Tag structure.",
    ),
}


TAGS_ELEMENTS: dict[str, ElementSpec] = {
    "Tag": ElementSpec(
        name="Tag",
        description="A controller- or program-scoped tag.",
        attributes=TAG_ATTRIBUTES,
        elements=TAG_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Tag structure.",
    ),
}
