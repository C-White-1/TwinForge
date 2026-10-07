"""Declarative selectors for the observed `.smbp` basic mapping profile.

Paths are relative child names. New layouts require evidence and an explicit
entry here; see docs/architecture/machine-expert-basic-smbp-format.md.
"""
from dataclasses import dataclass

PathSpec = tuple[str, ...]


@dataclass(frozen=True)
class SymbolTable:
    """A list of address-keyed entries that may carry `Symbol`/`Comment`."""

    name: str
    container: PathSpec
    entry: str


@dataclass(frozen=True)
class MappingSpec:
    project_root: str = "ProjectDescriptor"
    encrypted_root: str = "CryptedProject"
    project_name: PathSpec = ("Name",)
    project_version: PathSpec = ("ProjectVersion",)
    encrypted_project_name: PathSpec = ("PublicProperties", "ProjectInformations", "Name")
    cpu_reference: PathSpec = ("HardwareConfiguration", "Plc", "Cpu", "Reference")
    pous: PathSpec = ("SoftwareConfiguration", "Pous", "ProgramOrganizationUnits")
    pou_name: PathSpec = ("Name",)
    rungs: PathSpec = ("Rungs", "RungEntity")
    rung_comment: PathSpec = ("MainComment",)
    rung_cells: PathSpec = ("LadderElements", "LadderEntity")
    rung_instruction_lines: PathSpec = ("InstructionLines", "InstructionLineEntity")
    instruction_text: PathSpec = ("InstructionLine",)
    cell_element_type: PathSpec = ("ElementType",)
    # A placeholder cell with no wiring and no IL counterpart.
    placeholder_cell_type: str = "None"
    entry_address: PathSpec = ("Address",)
    entry_symbol: PathSpec = ("Symbol",)
    entry_comment: PathSpec = ("Comment",)
    symbol_tables: tuple[SymbolTable, ...] = (
        SymbolTable("DigitalInputs", ("HardwareConfiguration", "Plc", "Cpu", "DigitalInputs"), "DiscretInput"),
        SymbolTable("DigitalOutputs", ("HardwareConfiguration", "Plc", "Cpu", "DigitalOutputs"), "DiscretOutput"),
        SymbolTable("AnalogInputs", ("HardwareConfiguration", "Plc", "Cpu", "AnalogInputs"), "AnalogIO"),
        SymbolTable("AnalogOutputs", ("HardwareConfiguration", "Plc", "Cpu", "AnalogOutputs"), "AnalogIO"),
        SymbolTable("InputAssemblys", ("HardwareConfiguration", "Plc", "Cpu", "InputAssemblys"), "NetworkObject"),
        SymbolTable("OutputAssemblys", ("HardwareConfiguration", "Plc", "Cpu", "OutputAssemblys"), "NetworkObject"),
        SymbolTable("InputRegisters", ("HardwareConfiguration", "Plc", "Cpu", "InputRegisters"), "NetworkObject"),
        SymbolTable("HoldingRegisters", ("HardwareConfiguration", "Plc", "Cpu", "HoldingRegisters"), "NetworkObject"),
        SymbolTable("Cartridge1AnalogInputs", ("HardwareConfiguration", "Plc", "Cartridge1", "AnalogInputs"), "AnalogIO"),
        SymbolTable("Cartridge1AnalogOutputs", ("HardwareConfiguration", "Plc", "Cartridge1", "AnalogOutputs"), "AnalogIO"),
        SymbolTable("ExtensionAnalogInputs",
                    ("HardwareConfiguration", "Plc", "Extensions", "ModuleExtensionObject", "AnalogInputs"), "AnalogIO"),
        SymbolTable("ExtensionAnalogOutputs",
                    ("HardwareConfiguration", "Plc", "Extensions", "ModuleExtensionObject", "AnalogOutputs"), "AnalogIO"),
        SymbolTable("MemoryBits", ("SoftwareConfiguration", "MemoryBits"), "MemoryBit"),
        SymbolTable("MemoryWords", ("SoftwareConfiguration", "MemoryWords"), "MemoryWord"),
        SymbolTable("MemoryFloats", ("SoftwareConfiguration", "MemoryFloats"), "MemoryFloat"),
        SymbolTable("MemoryDoubleWords", ("SoftwareConfiguration", "MemoryDoubleWords"), "MemoryDoubleWord"),
        SymbolTable("Timers", ("SoftwareConfiguration", "Timers"), "TimerTM"),
        # Vendor-predefined system objects; every entry carries a symbol.
        SymbolTable("SystemBits", ("SoftwareConfiguration", "SystemBits"), "MemoryBit"),
        SymbolTable("SystemWords", ("SoftwareConfiguration", "SystemWords"), "MemoryWord"),
    )


BASIC_MAPPING = MappingSpec()
