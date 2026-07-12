from .reference import ReferenceType
from .spec import AttributeSpec, ElementSpec

CONTROLLER_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Use": AttributeSpec(
        name="Use",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 57",
    ),
    "Name": AttributeSpec(
        name="Name",
        description="The name of the controller component",
        l5x_only=False,
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
    "Code": AttributeSpec(
        name="Code",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "SFCExecutionControl": AttributeSpec(
        name="SFCExecutionControl",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "SFCRestartPosition": AttributeSpec(
        name="SFCRestartPosition",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "SFCLastScan": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 59",
    ),
    "ProjectSN": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "MatchProjectToController": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "InhibitAutomaticFirmwareUpdate": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "CurrentProjectLanguage": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "DefaultProjectLanguage": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "ControllerLanguage": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "CanUseRPIFromController": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "SecurityAuthorityID": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "SecurityAuthorityURI": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "PermissionSet": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "IsPermissionsSet": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "ChangesToDetect": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "TrustedSlots": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "PassThroughConfiguration": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "DownloadProjectDocumentationAndExtendedProperties": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "DownloadCustomProperties": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "EtherNetIPMode": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "SafetyEnabled": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "FrontPortCrossloadEnabledPorts": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "FrontPortCrossloadSecurityEnabled": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "ProjectCreationDate": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "LastModifiedDate": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "TargetName": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "TargetType": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "ContainsContext": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "ExportDate": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
    ),
    "ExportOptions": AttributeSpec(
        name="",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes",
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
        datatype=bool,
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "KeepTestEditsOnSwitchOver": AttributeSpec(
        name="KeepTestEditsOnSwitchOver",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "IOMemoryPadPercentage": AttributeSpec(
        name="IOMemoryPadPercentage",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
    "DataTablePadPercentage": AttributeSpec(
        name="DataTablePadPercentage",
        description="",
        l5x_only=True,
        valid_values=("Context", "Target"),
        manual_ref="1756-RM014D-EN-P September 2025, Chapter 2, Controller attributes. page 58",
    ),
}

SECURITY_ATTRIBUTES: dict[str, AttributeSpec] = {
    # Populate from the Security attributes table.
}

SAFETY_INFO_ATTRIBUTES: dict[str, AttributeSpec] = {
    # Populate from the SafetyInfo attributes table.
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
        manual_ref="1756-RM014D-EN-P, Chapter 2",
    ),
    "SafetyInfo": ElementSpec(
        name="SafetyInfo",
        description="Safety-controller configuration.",
        attributes=SAFETY_INFO_ATTRIBUTES,
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
    "PrimaryActionSet": ElementSpec(
        name="PrimaryActionSet",
        description="Primary action set configuration.",
        manual_ref="1756-RM014D-EN-P, Controller structure",
    ),
}
