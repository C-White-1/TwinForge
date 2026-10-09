"""Declarative selectors for the observed `.smbp` basic mapping profile.

Paths are relative child names. New layouts require evidence and an explicit
entry here; see docs/architecture/machine-expert-basic-smbp-format.md.
"""
from dataclasses import dataclass

PathSpec = tuple[str, ...]


@dataclass(frozen=True)
class SymbolTable:
    """A list of address-keyed entries that may carry `Symbol`/`Comment`.

    `data_type` is the IEC 61131-3 type of the table's objects, from
    Schneider's EcoStruxure Machine Expert - Basic Generic Functions Library
    Guide, EIO0000003289.04 (installed help `sombgflg.chm`):

    - bit objects `%I`, `%Q`, `%M`, `%S` ("Memory Bit Objects", "I/O
      Objects"): BOOL;
    - word objects `%MW`, `%KW`, `%IW`, `%QW`, `%IWS`, `%QWS`, `%SW` ("Word
      Objects": 16-bit two's complement, -32768..32767): INT;
    - network objects `%QWE`, `%IWE`, `%QWM`, `%IWM`: INT, because the guide's
      operand tables list them under "Words" with `%MW` ("Integer/Floating
      Conversion Instructions", "Word, Double Word, and Floating Point Tables
      Assignment");
    - `%MD` ("Floating Point and Double Word Objects": 32-bit two's
      complement): DINT;
    - `%MF` (same page: IEEE 754 single precision): REAL.

    Timers and counters are function-block instances, not elementary types,
    so they stay None.
    """

    name: str
    container: PathSpec
    entry: str
    data_type: str | None = None


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
        SymbolTable("DigitalInputs", ("HardwareConfiguration", "Plc", "Cpu", "DigitalInputs"), "DiscretInput", "BOOL"),
        SymbolTable("DigitalOutputs", ("HardwareConfiguration", "Plc", "Cpu", "DigitalOutputs"), "DiscretOutput",
                    "BOOL"),
        SymbolTable("AnalogInputs", ("HardwareConfiguration", "Plc", "Cpu", "AnalogInputs"), "AnalogIO", "INT"),
        SymbolTable("AnalogOutputs", ("HardwareConfiguration", "Plc", "Cpu", "AnalogOutputs"), "AnalogIO", "INT"),
        SymbolTable("InputAssemblys", ("HardwareConfiguration", "Plc", "Cpu", "InputAssemblys"), "NetworkObject",
                    "INT"),
        SymbolTable("OutputAssemblys", ("HardwareConfiguration", "Plc", "Cpu", "OutputAssemblys"), "NetworkObject",
                    "INT"),
        SymbolTable("InputRegisters", ("HardwareConfiguration", "Plc", "Cpu", "InputRegisters"), "NetworkObject",
                    "INT"),
        SymbolTable("HoldingRegisters", ("HardwareConfiguration", "Plc", "Cpu", "HoldingRegisters"), "NetworkObject",
                    "INT"),
        SymbolTable("Cartridge1AnalogInputs", ("HardwareConfiguration", "Plc", "Cartridge1", "AnalogInputs"),
                    "AnalogIO", "INT"),
        SymbolTable("Cartridge1AnalogOutputs", ("HardwareConfiguration", "Plc", "Cartridge1", "AnalogOutputs"),
                    "AnalogIO", "INT"),
        SymbolTable("ExtensionAnalogInputs",
                    ("HardwareConfiguration", "Plc", "Extensions", "ModuleExtensionObject", "AnalogInputs"), "AnalogIO",
                    "INT"),
        SymbolTable("ExtensionAnalogOutputs",
                    ("HardwareConfiguration", "Plc", "Extensions", "ModuleExtensionObject", "AnalogOutputs"), "AnalogIO",
                    "INT"),
        SymbolTable("MemoryBits", ("SoftwareConfiguration", "MemoryBits"), "MemoryBit", "BOOL"),
        SymbolTable("MemoryWords", ("SoftwareConfiguration", "MemoryWords"), "MemoryWord", "INT"),
        SymbolTable("MemoryFloats", ("SoftwareConfiguration", "MemoryFloats"), "MemoryFloat", "REAL"),
        SymbolTable("MemoryDoubleWords", ("SoftwareConfiguration", "MemoryDoubleWords"), "MemoryDoubleWord", "DINT"),
        SymbolTable("Timers", ("SoftwareConfiguration", "Timers"), "TimerTM"),
        # Written only when the counter is named or has non-default settings.
        SymbolTable("Counters", ("SoftwareConfiguration", "Counters"), "Counter"),
        # Vendor-predefined system objects; every entry carries a symbol.
        SymbolTable("SystemBits", ("SoftwareConfiguration", "SystemBits"), "MemoryBit", "BOOL"),
        SymbolTable("SystemWords", ("SoftwareConfiguration", "SystemWords"), "MemoryWord", "INT"),
    )


BASIC_MAPPING = MappingSpec()
