"""Observed `.smbp` grammar only; unknown content is always retained by capture.

Values are element text, not attributes (.NET XmlSerializer output), so most
entries declare child elements and no attributes.
"""
from dataclasses import dataclass, field

EVIDENCE = "docs/architecture/machine-expert-basic-smbp-format.md"


@dataclass(frozen=True)
class ElementSpec:
    name: str
    attributes: frozenset[str] = frozenset()
    children: tuple["ElementSpec", ...] = ()
    evidence: str = EVIDENCE
    status: str = field(default="observed", init=False)


def element(name: str, attributes: str = "", *children: ElementSpec) -> ElementSpec:
    return ElementSpec(name, frozenset(attributes.split()), children)


def leaves(*names: str) -> tuple[ElementSpec, ...]:
    return tuple(element(name) for name in names)


_SYMBOL = leaves("Address", "Index", "Symbol", "Comment")
_ANALOG_IO = element("AnalogIO", "", *_SYMBOL, *leaves(
    "Activation", "B", "ChartCalculation", "FallbackValue", "InputFilter", "IsInput",
    "Maximum", "Minimum", "R", "R1", "R2", "Reactivation", "Sampling", "Scope",
    "T", "T1", "T2", "Type"))
_NETWORK_OBJECT = element("NetworkObject", "", *_SYMBOL)

_LADDER_ENTITY = element("LadderEntity", "", *leaves(
    "ElementType", "Row", "Column", "ChosenConnection", "Descriptor", "Symbol", "Comment",
    "ComparisonExpression", "OperationExpression"))
_INSTRUCTION_LINE = element("InstructionLineEntity", "", *leaves("InstructionLine", "Comment"))
_RUNG = element("RungEntity", "",
                *leaves("Name", "Label", "MainComment", "IsLadderSelected"),
                element("LadderElements", "", _LADDER_ENTITY),
                element("InstructionLines", "", _INSTRUCTION_LINE))
_POU = element("ProgramOrganizationUnits", "",
               *leaves("Name", "SectionNumber"), element("Rungs", "", _RUNG))

_CPU = element(
    "Cpu", "",
    *leaves("Index", "InputNb", "OutputNb", "Kind", "Reference", "Name", "Consumption5V",
            "Consumption24V", "HardwareId", "IsExpander", "MaxCartridge"),
    element("DigitalInputs", "", element("DiscretInput", "", *_SYMBOL, *leaves("DIFiltering", "DILatch"))),
    element("DigitalOutputs", "", element("DiscretOutput", "", *_SYMBOL, element("FallbackValue"))),
    element("AnalogInputs", "", _ANALOG_IO),
    element("AnalogOutputs", "", _ANALOG_IO),
    element("InputAssemblys", "", _NETWORK_OBJECT),
    element("OutputAssemblys", "", _NETWORK_OBJECT),
    element("InputRegisters", "", _NETWORK_OBJECT),
    element("HoldingRegisters", "", _NETWORK_OBJECT),
)
_EXTENSION = element("ModuleExtensionObject", "",
                     *leaves("Index", "Reference", "Kind", "InputNb", "OutputNb", "HardwareId",
                             "IsExpander", "IsOptionnal", "Consumption5V", "Consumption24V"),
                     element("AnalogInputs", "", _ANALOG_IO),
                     element("AnalogOutputs", "", _ANALOG_IO))


def _table(container: str, entry: str, *extra: str) -> ElementSpec:
    return element(container, "", element(entry, "", *_SYMBOL, *leaves(*extra)))


PROJECT_SPEC = element(
    "ProjectDescriptor", "",
    *leaves("ProjectVersion", "ManagementLevel", "Name", "FullName", "CurrentCultureName"),
    element("HardwareConfiguration", "", element(
        "Plc", "", _CPU, element("Extensions", "", _EXTENSION),
        element("Cartridge1", "", element("AnalogInputs", "", _ANALOG_IO),
                element("AnalogOutputs", "", _ANALOG_IO)),
    )),
    element(
        "SoftwareConfiguration", "",
        element("Pous", "", _POU),
        _table("MemoryBits", "MemoryBit"),
        _table("MemoryWords", "MemoryWord"),
        _table("MemoryFloats", "MemoryFloat"),
        _table("MemoryDoubleWords", "MemoryDoubleWord"),
        _table("SystemBits", "MemoryBit"),
        _table("SystemWords", "MemoryWord"),
        _table("Timers", "TimerTM", "Preset", "Base", "Type", "IsRetentive", "IsDynamicPreset"),
        _table("Counters", "Counter", "Preset"),
    ),
    element("GlobalProperties"),
    element("DisplayUserLabelsConfiguration"),
    element("ReportConfiguration"),
)

ENCRYPTED_PROJECT_SPEC = element(
    "CryptedProject", "",
    element("ProjectVersion"), element("Crypted"),
    element("PublicProperties", "",
            element("ProjectInformations", "", element("Name")),
            element("CompanyInformations"), element("UserInformations")),
)

SPECS: tuple[ElementSpec, ...] = (PROJECT_SPEC, ENCRYPTED_PROJECT_SPEC)
