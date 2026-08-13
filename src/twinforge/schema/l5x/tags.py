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
        valid_values=("Base", "Alias", "Produced", "Consumed"),
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


PRODUCE_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    name: AttributeSpec(
        name=name,
        description=f"Logix produced-tag configuration field {name}.",
        manual_ref=(
            "1756-RM014D-EN-P September 2025, Produced tag attributes."
        ),
    )
    for name in (
        "ProduceCount",
        "MinimumRPI",
        "MaximumRPI",
        "DefaultRPI",
        "PLCMappingFile",
        "PLC2Mapping",
        "ProgrammaticallySendEventTrigger",
        "UnicastPermitted",
    )
}


CONSUME_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    name: AttributeSpec(
        name=name,
        description=f"Logix consumed-tag configuration field {name}.",
        manual_ref=(
            "1756-RM014D-EN-P September 2025, Consumed tag attributes."
        ),
    )
    for name in (
        "Producer",
        "RemoteTag",
        "RemoteFile",
        "RPI",
        "ProgrammaticallySendEventTrigger",
    )
}


TAG_DATA_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Format": AttributeSpec(
        name="Format",
        description="Serialization format of the enclosed tag data.",
        required=True,
        valid_values=("L5K", "Decorated", "String", "Alarm", "Message"),
        manual_ref="1756-RM014D-EN-P September 2025, Tag data structure.",
    ),
}

MESSAGE_PARAMETER_ATTRIBUTES: dict[str, AttributeSpec] = {
    name: AttributeSpec(
        name=name,
        description=f"Logix MESSAGE configuration field {name}.",
        manual_ref="1756-RM014D-EN-P September 2025, MESSAGE tag data.",
    )
    for name in (
        "MessageType",
        "RequestedLength",
        "ConnectedFlag",
        "ConnectionPath",
        "CommTypeCode",
        "ServiceCode",
        "ObjectType",
        "TargetObject",
        "AttributeNumber",
        "LocalIndex",
        "LocalElement",
        "DestinationTag",
        "LargePacketUsage",
    )
}

TAG_DATA_ELEMENTS: dict[str, ElementSpec] = {
    "MessageParameters": ElementSpec(
        name="MessageParameters",
        description="Configuration of a Logix MESSAGE tag.",
        attributes=MESSAGE_PARAMETER_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, MESSAGE tag data.",
    )
}


TAG_ELEMENTS: dict[str, ElementSpec] = {
    "ConsumeInfo": ElementSpec(
        name="ConsumeInfo",
        description="Remote producer configuration for a consumed tag.",
        attributes=CONSUME_INFO_ATTRIBUTES,
        manual_ref=(
            "1756-RM014D-EN-P September 2025, Consumed tag attributes."
        ),
    ),
    "ProduceInfo": ElementSpec(
        name="ProduceInfo",
        description="Consumer and packet interval configuration for a produced tag.",
        attributes=PRODUCE_INFO_ATTRIBUTES,
        manual_ref=(
            "1756-RM014D-EN-P September 2025, Produced tag attributes."
        ),
    ),
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
        elements=TAG_DATA_ELEMENTS,
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
