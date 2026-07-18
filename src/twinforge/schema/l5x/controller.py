from .reference import ReferenceType
from .spec import AttributeSpec, ElementSpec

CONTROLLER_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Use": AttributeSpec(
        name="Use",
        description="L5X only. Specify context or target.",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "Name": AttributeSpec(
        name="Name",
        description=(
            "L5X only. Specify the name of the controller component. "
            "In L5K, the name is an element of the controller component."
        ),
        l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "ProcessorType": AttributeSpec(
        name="ProcessorType",
        description="Specify the type of controller",
        l5x_only=False,
        valid_values=(
            "1756-L71",
            "1756-L71S",
            "1756-L72",
            "1756-L72S",
            "1756-L73",
            "1756-L73S",
            "1756-L74",
            "1756-L75",
            "1769-L16ER-BB1B",
            "1769-L18ER-BB1B",
            "1769-L18ERM-BB1B",
            "1769-L24ER-QB1B",
            "1769-L24ER-QBFC1B",
            "1769-L27ERM-QBFC1B",
            "1769-L30ER",
            "1769-L30ERM",
            "1769-L30ER-NSE",
            "1769-L33ER",
            "1769-L33ERM",
            "1769-L36ERM",
            "Emulator",
        ),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "MajorRev": AttributeSpec(
        name="MajorRev",
        description="Specify the major revision number (1...127) of the controller. ",
        l5x_only=True,
        minimum=1,
        maximum=127,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "MinorRev": AttributeSpec(
        name="MinorRev",
        description="Specify the minor revision number (1...127) of the controller.",
        l5x_only=True,
        minimum=1,
        maximum=127,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "TimeSlice": AttributeSpec(
        name="TimeSlice",
        description="Percentage of available CPU time (10...90) that is assigned to communication.",
        l5x_only=False,
        minimum=10,
        maximum=90,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "ShareUnusedTimeSlice": AttributeSpec(
        name="ShareUnusedTimeSlice",
        description="""Specify whether to share an unused timeslice or not.
        Type a 0 to not share; type a 1 to share.""",
        l5x_only=False,
        xml_type=int,
        datatype=bool,
        valid_values=(0, 1),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "PowerLossProgram": AttributeSpec(
        name="PowerLossProgram",
        description="Name of the program to be executed upon restart after a power loss.",
        l5x_only=False,
        datatype=str,
        target_type=ReferenceType.PROGRAM,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "MajorFaultProgram": AttributeSpec(
        name="MajorFaultProgram",
        description="Name of the program to be executed when a major fault occurs.",
        l5x_only=False,
        datatype=str,
        target_type=ReferenceType.PROGRAM,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "CommPath": AttributeSpec(
        name="CommPath",
        description=(
            r"Specify the devices in the communication path. The communication path ends with the controller "
            r"(\Backplane\1). This is exported only if you select manual configuration of the communication path in RSLinx software."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "CommDriver": AttributeSpec(
        name="CommDriver",
        description=(
            r"Specify the type of communication driver. This is the "
            r"name of the selected driver in RSLinx software. This is "
            r"exported only if you select manual configuration of the "
            r"communication driver in RSLinx software."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "SFCExecutionControl": AttributeSpec(
        name="SFCExecutionControl",
        description=(
            r"Specify whether the SFC executes the current active "
            r"steps before returning control (CurrentActive) or "
            r"whether the SFC executes all threads until reaching a "
            r"false transition (UntilFalse)."
        ),
        l5x_only=True,
        datatype=str,
        valid_values=("CurrentActive", "UntilFalse"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "SFCRestartPosition": AttributeSpec(
        name="SFCRestartPosition",
        description=(
            r"Specify whether the SFC restarts at the most recently "
            r"executed step (MostRecent) or at the initial step "
            r"(InitialStep)."
        ),
        l5x_only=True,
        datatype=str,
        valid_values=("MostRecent", "InitialStep"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "SFCLastScan": AttributeSpec(
        name="SFCLastScan",
        description=(
            r"Specify how the SFC manages its state on a last "
            r"scan. Select AutomaticReset, ProgrammaticReset, or "
            r"DontScan."
        ),
        l5x_only=True,
        datatype=str,
        valid_values=("AutomaticReset", "ProgrammaticReset", "DontScan"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "ProjectSN": AttributeSpec(
        name="ProjectSN",
        description=(
            r"L5X only. Specify the serial number of the controller. If a "
            r"serial number is specified, it is imported into the project "
            r"regardless of the MatchProjectToController setting. Type "
            r"a 32-bit, hexadecimal number with the 16# prefix, such "
            r"as 16#0012_E2BC"
        ),
        l5x_only=True,
        datatype=str,  # TODO(#13) replace with HexUInt32.
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "MatchProjectToController": AttributeSpec(
        name="MatchProjectToController",
        description=(
            r"Specify whether to be sure that the project matches the "
            r"controller or not. Type Yes or No."
        ),
        l5x_only=True,
        datatype=str,
        valid_values=("Yes", "No"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "InhibitAutomaticFirmwareUpdate": AttributeSpec(
        name="InhibitAutomaticFirmwareUpdate",
        description=(
            r"Specify whether to inhibit the automatic update of "
            r"controller firmware. Type a 0 to not inhibit; type a 1 to "
            r"inhibit."
        ),
        l5x_only=True,
        xml_type=int,
        datatype=bool,
        valid_values=(0, 1),  # or xml_type=int, datatype=bool in the future
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "CurrentProjectLanguage": AttributeSpec(
        name="CurrentProjectLanguage",
        description=(
            r"Specify the current project language for a project "
            r"documentation project."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "DefaultProjectLanguage": AttributeSpec(
        name="DefaultProjectLanguage",
        description=(
            r"Specify the default project language for a project "
            r"document at on project."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "ControllerLanguage": AttributeSpec(
        name="ControllerLanguage",
        description=(
            r"Specify the controller project language for a project "
            r"document at on project."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "CanUseRPIFromController": AttributeSpec(
        name="CanUseRPIFromController",
        description=(
            r"Specify whether the consumed tags in the controller "
            r"can connect to the producer with an RPI provided by the "
            r"producer (true or false)."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "PassThroughConfiguration": AttributeSpec(
        name="PassThroughConfiguration",
        description=(
            r"For L5K and L5X. Indicates the pass through state of "
            r"documentation for the project. "
            r"Type Disabled, Enabled, or EnabledWithAppend"
        ),
        l5x_only=False,
        datatype=str,
        valid_values=("Disabled", "Enabled", "EnabledWithAppend"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
    "DownloadProjectDocumentationAndExtendedProperties": AttributeSpec(
        name="DownloadProjectDocumentationAndExtendedProperties",
        description=(
            r"For L5K and L5X. Indicates the download project "
            r"documentation configuration setting of the project."
        ),
        l5x_only=False,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false", "Yes", "No"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
    "DownloadCustomProperties": AttributeSpec(
        name="DownloadCustomProperties",
        description=(
            r"For L5K and L5X. Indicates the download custom "
            r"properties configuration setting of the project. "
            r"Only applies if the project is already configured to "
            r"DownloadProjectDocumentation. "
            r"Rockwell recommends setting this attribute to false "
            r"only during startup testing to improve download speeds "
            r"during commissioning testing. It should be set to true "
            r"for the normal operating state of a system. For L5X, the "
            r"setting is true or false. For L5K, the setting is 1 (true) or "
            r"0 (false)."
        ),
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false", "1", "0"),
        l5x_only=False,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
    "EtherNetIPMode": AttributeSpec(
        name="EtherNetIPMode",
        description=(
            r"The EtherNet/IP Mode describes the relationship "
            r"between the CIP EtherNet/IP ports and the physical "
            r"Ethernet ports. The CIP EtherNet/IP port can be "
            r"configured as one of two modes: "
            r"• Dual-IP"
            r"• Linear/DLR"
        ),
        l5x_only=True,
        valid_values=("Dual-IP", "Linear/DLR"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
    "ProjectCreationDate": AttributeSpec(
        name="ProjectCreationDate",
        description="Observed L5X export metadata recording when the project was created.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
    "LastModifiedDate": AttributeSpec(
        name="LastModifiedDate",
        description="Observed L5X export metadata recording when the project was last modified.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
    "TargetName": AttributeSpec(
        name="TargetName",
        description="Observed L5X export metadata identifying the target component name.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
    "TargetType": AttributeSpec(
        name="TargetType",
        description="Observed L5X export metadata identifying the target component type.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
    "ContainsContext": AttributeSpec(
        name="ContainsContext",
        description="Observed L5X export metadata indicating whether context is included.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
    "ExportDate": AttributeSpec(
        name="ExportDate",
        description="Observed L5X export metadata recording when the file was exported.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
    "ExportOptions": AttributeSpec(
        name="ExportOptions",
        description="Observed L5X export metadata describing selected export options.",
        l5x_only=True,
        datatype=str,
        manual_ref="Observed in L5X exports; not listed in Chapter 2 controller attributes table.",
    ),
}

REDUNDANCY_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Enabled": AttributeSpec(
        name="Enabled",
        description=(
            r"L5X only. Specify whether redundancy is used (true or "
            r"false)."
            r"This attribute is on the <RedundancyInfo> tag element."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "KeepTestEditsOnSwitchOver": AttributeSpec(
        name="KeepTestEditsOnSwitchOver",
        description=(
            r"Specify whether to keep test edits on when a switchover "
            r"occurs in a redundant system. Type a 0 not to keep test "
            r"edits on; type a 1 to keep test edits on. "
            r"For L5X, this attribute is on the <RedundancyInfo> tag "
            r"element. Type false or true."
        ),
        l5x_only=False,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "IOMemoryPadPercentage": AttributeSpec(
        name="IOMemoryPadPercentage",
        description=(
            r"Specify the percentage (0...100) of I/O memory that "
            r"is available to the system after the download when "
            r"configured for redundancy. "
            r"For L5X, this attribute is on the <RedundancyInfo> tag "
            r"element."
        ),
        l5x_only=True,
        datatype=int,
        minimum=0,
        maximum=100,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "DataTablePadPercentage": AttributeSpec(
        name="DataTablePadPercentage",
        description=(
            r"Specify the percentage (0...100) of the data table "
            r"to reserve. If redundancy is not enabled, type 0. If "
            r"redundancy is enabled, type 50. "
            r"For L5X, this attribute is on the <RedundancyInfo> tag "
            r"element"
        ),
        l5x_only=True,
        datatype=int,
        minimum=0,  # TODO(#14) Add validation logic
        maximum=100,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "FrontPortCrossloadEnabledPorts": AttributeSpec(
        name="FrontPortCrossloadEnabledPorts",
        description=(
            r"L5K and L5X. Export the Front Port Crossload "
            r"Enabled/Disabled selection value: "
            r"• When FrontPortCrossloadEnabledPorts is selected, "
            r"the attribute value is 1,2. "
            r"• When FrontPortCrossloadEnabledPorts is cleared, "
            r"the attribute value is "
            ". "
            r"When selected, the value is exported regardless of "
            r"redundancy state. "
            r"For L5X, this attribute is on the <RedundancyInfo> tag "
            r"element."
        ),
        l5x_only=False,
        datatype=str,
        valid_values=("1,2", ""),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 61",
    ),
    "FrontPortCrossloadSecurityEnabled": AttributeSpec(
        name="FrontPortCrossloadSecurityEnabled",
        description=(
            r"L5K and L5X. Export the Front Port Crossload Security "
            r"Enabled/Disabled selection: "
            r"• When FrontPortCrossloadSecurityEnabled is "
            r"selected, the exported value is true. "
            r"• When FrontPortCrossloadSecurityEnabled is "
            r"cleared, the exported value is false. "
            r"When selected, the value is exported regardless of "
            r"redundancy state. "
            r"For L5X, this attribute is on the <RedundancyInfo> tag "
            r"element."
        ),
        l5x_only=False,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 61",
    ),
}

SECURITY_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Code": AttributeSpec(
        name="Code",
        description=(
            r"L5X only. Specify whether the RSI Security Server is "
            r"enabled for the controller. Type 0 if the controller is "
            r"unsecured; type a 10-digit, non-zero value if the "
            r"controller is secured. This attribute is on the "
            r"<Security> tag element."
        ),
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "ChangesToDetect": AttributeSpec(
        name="ChangesToDetect",
        description=(
            r"Mask that specifies the controller events that you wish to track."
            r"For L5X only, this attribute is on the <Security> tag "
            r"element."
        ),
        l5x_only=True,
        datatype=str,  # TODO(#13) replace with HexMask.
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "SecurityAuthorityID": AttributeSpec(
        name="SecurityAuthorityID",
        description=(
            r"ID of the FactoryTalk Diagnostics® to which your "
            r"controller is bound. "
            r"For L5X only, this attribute is on the <Security> tag "
            r"element."
        ),
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "SecurityAuthorityURI": AttributeSpec(
        name="SecurityAuthorityURI",
        description=(
            r"Network path to the FactoryTalk Diagnostics to which "
            r"your controller is bound. "
            r"For L5X only, this attribute is on the <Security> tag "
            r"element."
        ),
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "PermissionSet": AttributeSpec(
        name="PermissionSet",
        description=(
            r"Name of the set of permissions, configured in "
            r"FactoryTalk Security, to apply to this object. "
            r"For L5X only, this attribute is on the <Security> tag"
            r"element."
        ),
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "TrustedSlots": AttributeSpec(
        name="TrustedSlots",
        description=(
            r"Mask defining the slots through which the trusted "
            r"communication is permitted to the controller. "
            r"For L5X only, this attribute is on the <Security> tag "
            r"element"
        ),
        l5x_only=True,
        datatype=str,  # TODO(#13): Replace with HexMask once implemented. Possibly BitMask TBD
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
}

PRIMARY_ACTION_SET_ATTRIBUTES: dict[str, AttributeSpec] = {
    "PermissionSet": AttributeSpec(
        name="PermissionSet",
        description=(
            r"Name of the permission set or logical name associated "
            r"with this cached permissions entry."
        ),
        l5x_only=True,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 53",
    ),
    "IsPermissionSet": AttributeSpec(
        name="IsPermissionSet",
        description=(
            r"Indicates if this is associated with a permission set or a "
            r"logical name."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
}

SECURITY_ELEMENTS: dict[str, ElementSpec] = {
    "PrimaryActionSets": ElementSpec(
        name="PrimaryActionSets",
        description="Container for cached permission entries.",
        elements={
            "PrimaryActionSet": ElementSpec(
                name="PrimaryActionSet",
                description=(
                    "Cache of permissions associated with the specified "
                    "logical name or permission set."
                ),
                attributes=PRIMARY_ACTION_SET_ATTRIBUTES,
                repeatable=True,
                content_type="cdata",
                manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 53",
            ),
        },
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 53",
    ),
}

SAFETY_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    "SafetyEnabled": AttributeSpec(
        name="SafetyEnabled",
        description=(
            r"L5K and L5X. For controllers that support enabling and "
            r"disabling safety, the Safety Enabled setting checkbox "
            r"value. "
            r"For L5X, this attribute is on the <SafetyInfo> tag "
            r"element"
        ),
        l5x_only=False,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 60",
    ),
    "SafetySignature": AttributeSpec(
        name="SafetySignature",
        description=(
            r"Specifies the safety signature control as defined in the "
            r"controller properties. This value is exported only; it is "
            r"ignored on import. "
            r"For L5X, this attribute is on the <SafetyInfo> tag "
            r"element"
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 61",
        notes="Export only; ignored on import.",
    ),
    "SafetyLocked": AttributeSpec(
        name="SafetyLocked",
        description=(
            r"Displays whether the safety controller is locked or not. "
            r"For L5X, this attribute is on the <SafetyInfo> tag element. "
            r"Type true or false."
        ),
        l5x_only=False,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 61",
        notes="Export only; ignored on import.",
    ),
    "SafetyLockPassword": AttributeSpec(
        name="SafetyLockPassword",
        description=(
            r"Specifies the lock password in the controller. This value "
            r"is encrypted on export. For L5X, this attribute is on the "
            r"<SafetyInfo> tag element."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 61",
    ),
    "SafetyUnlockPassword": AttributeSpec(
        name="SafetyUnlockPassword",
        description=(
            r"Specifies the unlock password in the controller. This value "
            r"is encrypted on export. For L5X, this attribute is on the "
            r"<SafetyInfo> tag element."
        ),
        l5x_only=False,
        datatype=str,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 62",
    ),
    "ConfigureSafetyIOAlways": AttributeSpec(
        name="ConfigureSafetyIOAlways",
        description=(
            r"Specify whether to configure safety I/O when replacing "
            r"safety I/O. For L5X, this attribute is on the <SafetyInfo> "
            r"tag element. Type true or false."
        ),
        l5x_only=False,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 62",
    ),
    "SignatureRunModeProtect": AttributeSpec(
        name="SignatureRunModeProtect",
        description=(
            r"Indicates whether you can modify the safety signature when "
            r"in Run mode. For L5X only, this attribute is on the "
            r"<SafetyInfo> tag element."
        ),
        l5x_only=True,
        xml_type=str,
        datatype=bool,
        valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 62",
    ),
}

SAFETY_INFO_ELEMENTS: dict[str, ElementSpec] = {
    "SafetyTagMap": ElementSpec(
        name="SafetyTagMap",
        description=(
            "L5X safety tag map body. Mappings are separated with a "
            "comma and a space."
        ),
        content_type="text",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes in a safety controller system. page 62",
    ),
}

DATATYPE_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    # Populate from the SafetyInfo attributes table.
}

MODULE_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    # Populate from the SafetyInfo attributes table.
}

CONTROLLER_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description",
        description="Controller description stored as CDATA text.",
        content_type="cdata",
        manual_ref="1756-RM014D-EN-P, Chapter 2, L5X controller structure",
    ),
    "RedundancyInfo": ElementSpec(
        name="RedundancyInfo",
        description="Controller redundancy configuration.",
        attributes=REDUNDANCY_INFO_ATTRIBUTES,
        manual_ref="1756-RM014D-EN-P, Chapter 2",
    ),
    "Security": ElementSpec(
        name="Security",
        description="Controller security configuration.",
        attributes=SECURITY_ATTRIBUTES,
        elements=SECURITY_ELEMENTS,
        manual_ref="1756-RM014D-EN-P, Chapter 2",
    ),
    "SafetyInfo": ElementSpec(
        name="SafetyInfo",
        description="Safety-controller configuration.",
        attributes=SAFETY_INFO_ATTRIBUTES,
        elements=SAFETY_INFO_ELEMENTS,
        manual_ref="1756-RM014D-EN-P, Chapter 2",
    ),
    "DataTypes": ElementSpec(
        name="DataTypes",
        description="Container for controller data type definitions.",
        manual_ref="1756-RM014D-EN-P, Chapter 2",
    ),
    "Modules": ElementSpec(
        name="Modules",
        description="Container for controller module definitions.",
        manual_ref="1756-RM014D-EN-P, Chapter 2",
    ),
    "AddOnInstructionDefinitions": ElementSpec(
        name="AddOnInstructionDefinitions",
        description="Container for Add-On Instruction definitions.",
        manual_ref="1756-RM014D-EN-P, Chapter 5",
    ),
    "Tags": ElementSpec(
        name="Tags",
        description="Container for controller-scoped tags.",
        manual_ref="1756-RM014D-EN-P, Chapter 6",
    ),
    "Programs": ElementSpec(
        name="Programs",
        description="Container for controller programs.",
        manual_ref="1756-RM014D-EN-P, Chapter 7",
    ),
    "Tasks": ElementSpec(
        name="Tasks",
        description="Container for controller task definitions.",
        manual_ref="1756-RM014D-EN-P, Chapter 14",
    ),
    "ParameterConnections": ElementSpec(
        name="ParameterConnections",
        description="Container for program parameter connections.",
        manual_ref="1756-RM014D-EN-P, Chapter 15",
    ),
    "Trends": ElementSpec(
        name="Trends",
        description="Container for configured trends.",
        manual_ref="1756-RM014D-EN-P, Chapter 16",
    ),
    "QuickWatchLists": ElementSpec(
        name="QuickWatchLists",
        description="Container for quick watch lists.",
        manual_ref="1756-RM014D-EN-P, Chapter 17",
    ),
    "CommPorts": ElementSpec(
        name="CommPorts",
        description="Controller communication port configuration.",
        manual_ref="1756-RM014D-EN-P, Controller configuration objects, Chapter 18",
    ),
    "CST": ElementSpec(
        name="CST",
        description="Coordinated System Time configuration.",
        manual_ref="1756-RM014D-EN-P, Controller configuration objects, Chapter 18",
    ),
    "WallClockTime": ElementSpec(
        name="WallClockTime",
        description="Controller wall-clock time configuration.",
        manual_ref="1756-RM014D-EN-P, Controller configuration objects, Chapter 18",
    ),
    "InternetProtocol": ElementSpec(
        name="InternetProtocol",
        description="Controller Internet Protocol configuration.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 55",
    ),
    "EthernetPorts": ElementSpec(
        name="EthernetPorts",
        description="Container for controller Ethernet port configuration.",
        elements={
            "EthernetPort": ElementSpec(
                name="EthernetPort",
                description="Controller Ethernet port configuration.",
                repeatable=True,
                manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 55",
            ),
        },
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 55",
    ),
    "EthernetNetwork": ElementSpec(
        name="EthernetNetwork",
        description="Controller Ethernet network configuration.",
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, L5X controller structure. page 55",
    ),
}
