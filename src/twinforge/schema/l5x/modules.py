from .spec import AttributeSpec, ElementSpec

MODULE_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name",
        description=(
            "L5X only. Specify the name of the module. "
            "In L5K, the name is an element of the statement."
        ),
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "ParentModule": AttributeSpec(
        name="ParentModule",
        description=(
            "L5X only. If this module is a child to another module, "
            "specify the name of the parent module."
        ),
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "ParentModPortId": AttributeSpec(
        name="ParentModPortId",
        description=(
            "If this module is a child to another module, specify the "
            "number of the port on the parent module that connects to "
            "this child module."
        ),
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
        notes=(
            "The manual renders this as ParentModPortID, but observed "
            "L5X exports use ParentModPortId."
        ),
    ),
    "CatalogNumber": AttributeSpec(
        name="CatalogNumber",
        description="Specify the catalog number of the module.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "Vendor": AttributeSpec(
        name="Vendor",
        description="Specify the numeric vendor identifier of the module.",
        datatype=int,
        value_labels=((1, "Allen-Bradley / Rockwell Automation"),),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "ProductType": AttributeSpec(
        name="ProductType",
        description="Specify the product type of the module.",
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "ProductCode": AttributeSpec(
        name="ProductCode",
        description="Specify the product code of the module.",
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "Major": AttributeSpec(
        name="Major",
        description="Specify the major revision number of the module.",
        datatype=int,
        minimum=1,
        maximum=127,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "Minor": AttributeSpec(
        name="Minor",
        description="Specify the minor revision number of the module.",
        datatype=int,
        minimum=1,
        maximum=255,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 82",
    ),
    "Mode": AttributeSpec(
        name="Mode",
        description="Select a specific mode by setting the appropriate bit.",
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 83",
    ),
    "DtlsFileName": AttributeSpec(
        name="DtlsFileName",
        description="Specify the file name associated with a DriveExecutive project.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "ConfigCode": AttributeSpec(
        name="ConfigCode",
        description="Specify the value that represents the drive rating of the drive.",
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "ControlNetSignature": AttributeSpec(
        name="ControlNetSignature",
        description=(
            "Hexadecimal value exported only for file compare and ignored "
            "on import."
        ),
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "SafetyNetwork": AttributeSpec(
        name="SafetyNetwork",
        description=(
            "If the module is in a safety controller system, specify the "
            "6-byte hexadecimal number of the safety network."
        ),
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "SafetyEnabled": AttributeSpec(
        name="SafetyEnabled",
        description=(
            "A flag only in modules that can be configured as safety or "
            "standard. Type true if the module is a safety module."
        ),
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "Inhibited": AttributeSpec(
        name="Inhibited",
        description=(
            "L5X only. If the module is inhibited, type true. If the "
            "module is not inhibited, type false."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "MajorFault": AttributeSpec(
        name="MajorFault",
        description=(
            "L5X only. Specify if the controller generates a major fault "
            "if the connection to the module is lost in run mode."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "ShutdownParentOnFault": AttributeSpec(
        name="ShutdownParentOnFault",
        description="Indicates the parent device is shut down when this module faults.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "DrivesADCMode": AttributeSpec(
        name="DrivesADCMode",
        description="Sets or clears the Drives ADC mode bit.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "DrivesADCEnabled": AttributeSpec(
        name="DrivesADCEnabled",
        description="Indicates that Automatic Device Configuration is enabled.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "UserDefinedCatalogNumber": AttributeSpec(
        name="UserDefinedCatalogNumber",
        description="Used to persist the catalog number for drive peripherals.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "Constant": AttributeSpec(
        name="Constant",
        description=(
            "Specify whether the value is a constant value or a dynamic "
            "value. For L5X, specify true or false."
        ),
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "PermissionSet": AttributeSpec(
        name="PermissionSet",
        description=(
            "Name of the set of permissions, configured in FactoryTalk "
            "Security, to apply to this object."
        ),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
}

EKEY_ATTRIBUTES: dict[str, AttributeSpec] = {
    "State": AttributeSpec(
        name="State",
        description=(
            "L5X only. Type CompatibleModule, ExactMatch, Disabled, or Custom."
        ),
        l5x_only=True,
        valid_values=("CompatibleModule", "ExactMatch", "Disabled", "Custom"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 84",
    ),
    "Vendor": AttributeSpec(
        name="Vendor",
        description="Vendor keying value used when State is Custom.",
        datatype=int,
        value_labels=((1, "Allen-Bradley / Rockwell Automation"),),
        applicable_when=(("State", ("Custom",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "ProductType": AttributeSpec(
        name="ProductType",
        description="Product type keying value used when State is Custom.",
        datatype=int,
        applicable_when=(("State", ("Custom",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "ProductCode": AttributeSpec(
        name="ProductCode",
        description="Product code keying value used when State is Custom.",
        datatype=int,
        applicable_when=(("State", ("Custom",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "Major": AttributeSpec(
        name="Major",
        description="Major revision keying value used when State is Custom.",
        datatype=int,
        applicable_when=(("State", ("Custom",)),),
        minimum=1,
        maximum=127,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 81",
    ),
    "Minor": AttributeSpec(
        name="Minor",
        description="Minor revision keying value used when State is Custom.",
        datatype=int,
        applicable_when=(("State", ("Custom",)),),
        minimum=1,
        maximum=255,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 82",
    ),
}

BUS_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Size": AttributeSpec(
        name="Size",
        description="L5X only. For a sizable chassis, specify the chassis size.",
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "Baud": AttributeSpec(
        name="Baud",
        description="L5X only. Specify the bus baud rate.",
        l5x_only=True,
        valid_values=("57.6", "115.2", "230.4"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
}

PORT_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Id": AttributeSpec(
        name="Id",
        description="L5X only. Uniquely identifies the port.",
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "Address": AttributeSpec(
        name="Address",
        description="L5X only. Specify the node number, slot number, or address.",
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "Type": AttributeSpec(
        name="Type",
        description="L5X only. Defines the type of module port.",
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "Upstream": AttributeSpec(
        name="Upstream",
        description=(
            "L5X only. Specify true for upstream or false for downstream."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "NATActualAddress": AttributeSpec(
        name="NATActualAddress",
        description="Actual IP address on the network of the module.",
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "ConnectorOffset": AttributeSpec(
        name="ConnectorOffset",
        description="L5X only. Connector offset for the port.",
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
    "Width": AttributeSpec(
        name="Width",
        description="L5X only. Width for the port.",
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 86",
    ),
}

CONFIG_TAG_ATTRIBUTES: dict[str, AttributeSpec] = {
    "ConfigSize": AttributeSpec(
        name="ConfigSize",
        description="L5X only. Specify the size of the ConfigTag.",
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 85",
    ),
    "ExternalAccess": AttributeSpec(
        name="ExternalAccess",
        description="Observed L5X export metadata for module configuration tag access.",
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 4 module attributes table.",
    ),
}

CONFIG_SCRIPT_ATTRIBUTES: dict[str, AttributeSpec] = {
    "ConfigSize": AttributeSpec(
        name="ConfigSize",
        description="Observed L5X export metadata for module configuration script size.",
        l5x_only=True,
        datatype=int,
        manual_ref="Observed in L5X exports; related to Chapter 4 ConfigScript structure.",
    ),
}

COMMUNICATIONS_ATTRIBUTES: dict[str, AttributeSpec] = {
    "CommMethod": AttributeSpec(
        name="CommMethod",
        description="Specify the method of connecting to the module.",
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 83",
    ),
    "ConfigMethod": AttributeSpec(
        name="ConfigMethod",
        description="Specify the method of configuring the module.",
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 83",
    ),
    "PrimCxnInputSize": AttributeSpec(
        name="PrimCxnInputSize",
        description="Size of input data associated with the primary connection.",
        datatype=int,
        minimum=0,
        maximum=500,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 84",
    ),
    "PrimCxnOutputSize": AttributeSpec(
        name="PrimCxnOutputSize",
        description="Size of output data associated with the primary connection.",
        datatype=int,
        minimum=0,
        maximum=496,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 84",
    ),
    "SecCxnInputSize": AttributeSpec(
        name="SecCxnInputSize",
        description="Size of input data associated with the secondary connection.",
        datatype=int,
        minimum=0,
        maximum=500,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 84",
    ),
    "SecCxnOutputSize": AttributeSpec(
        name="SecCxnOutputSize",
        description="Size of output data associated with the secondary connection.",
        datatype=int,
        minimum=0,
        maximum=496,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module attributes. page 84",
    ),
}

CONNECTION_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name",
        description=(
            "L5X only. Specify the name of the connection. "
            "In L5K, the name is an element of the statement."
        ),
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 89",
    ),
    "RPI": AttributeSpec(
        name="RPI",
        description="L5X only. Requested packet interval rate in microseconds.",
        l5x_only=True,
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 89",
    ),
    "InputCxnPoint": AttributeSpec(
        name="InputCxnPoint",
        description="Specify the input connection point for the primary connection.",
        datatype=int,
        minimum=0,
        maximum=255,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 89",
    ),
    "InputSize": AttributeSpec(
        name="InputSize",
        description="Specify the input size.",
        datatype=int,
        minimum=0,
        maximum=255,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 89",
    ),
    "OutputCxnPoint": AttributeSpec(
        name="OutputCxnPoint",
        description="Specify the output connection point for the primary connection.",
        datatype=int,
        minimum=0,
        maximum=255,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 89",
    ),
    "OutputSize": AttributeSpec(
        name="OutputSize",
        description="Specify the output size.",
        datatype=int,
        minimum=0,
        maximum=255,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 89",
    ),
    "Unicast": AttributeSpec(
        name="Unicast",
        description="Specify if the EtherNet/IP connection is unicast.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "EventID": AttributeSpec(
        name="EventID",
        description="Specify the event ID if used with an event task.",
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "ControlNetScheduled": AttributeSpec(
        name="ControlNetScheduled",
        description="Specify how the connection is scheduled over ControlNet.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "Type": AttributeSpec(
        name="Type",
        description="L5X only. Specify the type of connection.",
        l5x_only=True,
        valid_values=(
            "Input",
            "Output",
            "MotionSync",
            "MotionAsync",
            "MotionEvent",
            "SafetyInput",
            "SafetyOutput",
        ),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "Priority": AttributeSpec(
        name="Priority",
        description="Indicates the rank of the input production.",
        valid_values=("Scheduled", "High"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "InputConnectionType": AttributeSpec(
        name="InputConnectionType",
        description="Indicates the type of input production.",
        valid_values=("Multicast", "Unicast"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "OutputRedundantOwner": AttributeSpec(
        name="OutputRedundantOwner",
        description="Indicates if the output production is a redundant owner.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "InputProductionTrigger": AttributeSpec(
        name="InputProductionTrigger",
        description="Indicates the input production trigger.",
        valid_values=("Cyclic", "COS", "Application"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "ConnectionPath": AttributeSpec(
        name="ConnectionPath",
        description="Indicates the target connection path.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "InputTagSuffix": AttributeSpec(
        name="InputTagSuffix",
        description="Identifies the suffix for the input tag.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "OutputTagSuffix": AttributeSpec(
        name="OutputTagSuffix",
        description="Identifies the suffix for the output tag.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes. page 90",
    ),
    "ProgrammaticallySendEventTrigger": AttributeSpec(
        name="ProgrammaticallySendEventTrigger",
        description="Observed L5X export metadata for event trigger behavior.",
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="Observed in L5X exports; not listed in Chapter 4 module connection attributes table.",
    ),
    "TimeoutMultiplier": AttributeSpec(
        name="TimeoutMultiplier",
        description="Safety connection timeout multiplier.",
        datatype=int,
        minimum=1,
        maximum=4,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes in a safety controller system. page 91",
    ),
    "NetworkDelayMultiplier": AttributeSpec(
        name="NetworkDelayMultiplier",
        description="Safety connection network delay multiplier percentage.",
        datatype=int,
        minimum=10,
        maximum=600,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes in a safety controller system. page 91",
    ),
    "ReactionTimeLimit": AttributeSpec(
        name="ReactionTimeLimit",
        description="Safety connection reaction time limit.",
        datatype=int,
        minimum=0,
        maximum=5500032,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes in a safety controller system. page 91",
    ),
    "MaxObservedNetworkDelay": AttributeSpec(
        name="MaxObservedNetworkDelay",
        description=(
            "Exported informational measure of the longest safety packet "
            "network delay; ignored on import."
        ),
        datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module connection attributes in a safety controller system. page 91",
    ),
}

TAG_DATA_ATTRIBUTES: dict[str, AttributeSpec] = {
    "ExternalAccess": AttributeSpec(
        name="ExternalAccess",
        description="Observed L5X export metadata for connection tag access.",
        datatype=str,
        manual_ref="Observed in L5X exports; connection tag data is module-specific.",
    ),
}

CONNECTION_ELEMENTS: dict[str, ElementSpec] = {
    "InputTag": ElementSpec(
        name="InputTag",
        description="Input channel data.",
        attributes=TAG_DATA_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Connection elements. page 89",
    ),
    "OutputTag": ElementSpec(
        name="OutputTag",
        description="Output channel data.",
        attributes=TAG_DATA_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Connection elements. page 89",
    ),
    "InAliasTag": ElementSpec(
        name="InAliasTag",
        description="Rack connection input alias tag data.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X connection structure. page 88",
    ),
    "OutAliasTag": ElementSpec(
        name="OutAliasTag",
        description="Rack connection output alias tag data.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X connection structure. page 88",
    ),
}

CONNECTIONS_ELEMENTS: dict[str, ElementSpec] = {
    "Connection": ElementSpec(
        name="Connection",
        description="Connection characteristics for the module.",
        attributes=CONNECTION_ATTRIBUTES,
        elements=CONNECTION_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X connection structure. page 87",
    ),
    "RackConnection": ElementSpec(
        name="RackConnection",
        description="Rack connection characteristics for the module.",
        attributes=CONNECTION_ATTRIBUTES,
        elements=CONNECTION_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X connection structure. page 88",
    ),
}

COMMUNICATIONS_ELEMENTS: dict[str, ElementSpec] = {
    "ConfigTag": ElementSpec(
        name="ConfigTag",
        description="Operating characteristics of the module.",
        attributes=CONFIG_TAG_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X module structure. page 79",
    ),
    "ConfigScript": ElementSpec(
        name="ConfigScript",
        description="Configuration script for the module.",
        attributes=CONFIG_SCRIPT_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X module structure. page 79",
    ),
    "Connections": ElementSpec(
        name="Connections",
        description="Container for module connection characteristics.",
        elements=CONNECTIONS_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X connection structure. page 87",
    ),
}

PORT_ELEMENTS: dict[str, ElementSpec] = {
    "Bus": ElementSpec(
        name="Bus",
        description="Bus information for a module port.",
        attributes=BUS_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X module structure. page 79",
    ),
}

PORTS_ELEMENTS: dict[str, ElementSpec] = {
    "Port": ElementSpec(
        name="Port",
        description="Physical connector for the module.",
        attributes=PORT_ATTRIBUTES,
        elements=PORT_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module elements. page 81",
    ),
}

MODULE_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description",
        description="User information about the module.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module elements. page 80",
    ),
    "EKey": ElementSpec(
        name="EKey",
        description="Keying information for the module.",
        attributes=EKEY_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module elements. page 80",
    ),
    "Ports": ElementSpec(
        name="Ports",
        description="Container for module port information.",
        elements=PORTS_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module elements. page 81",
    ),
    "Communications": ElementSpec(
        name="Communications",
        description="Module communication and configuration data.",
        attributes=COMMUNICATIONS_ATTRIBUTES,
        elements=COMMUNICATIONS_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X module structure. page 79",
    ),
    "ExtendedProperties": ElementSpec(
        name="ExtendedProperties",
        description="Additional profile data stored in XML format.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, Module elements. page 81",
    ),
}

MODULES_ELEMENTS: dict[str, ElementSpec] = {
    "Module": ElementSpec(
        name="Module",
        description="A module used by exported logic.",
        attributes=MODULE_ATTRIBUTES,
        elements=MODULE_ELEMENTS,
        repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 4, L5X module structure. page 79",
    ),
}
