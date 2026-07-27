"""Manual-backed PowerFlex 525 parameter catalogue knowledge."""

from __future__ import annotations

from twinforge.model import (
    DeviceParameterDefinition,
    DeviceParameterField,
    DeviceParameterFlag,
    DeviceParameterOption,
)


POWERFLEX_525_PARAMETER_REFERENCE = (
    "Rockwell Automation Publication 520-UM001L-EN-E, "
    "PowerFlex 520-Series Adjustable Frequency AC Drive User Manual, "
    "March 2022"
)

POWERFLEX_525_PARAMETER_GROUPS = {
    "b": "Basic Display",
    "p": "Basic Program",
    "t": "Terminal Block",
    "c": "Communications",
    "d": "Advanced Display",
    "a": "Advanced Program",
    "f": "Fault and Diagnostic",
}


class PowerFlex525ParameterCatalogue:
    """Look up curated facts from the cited PowerFlex user manual."""

    def curated_numbers(self) -> tuple[int, ...]:
        """Return curated parameter numbers in deterministic order."""

        return tuple(sorted(_PARAMETERS))

    def definition(self, number: int) -> DeviceParameterDefinition | None:
        """Return a definition when that parameter has been curated."""

        return _PARAMETERS.get(number)

    def group_name(self, prefix: str | None) -> str | None:
        """Resolve a parameter-group prefix without changing its spelling."""

        if prefix is None:
            return None
        return POWERFLEX_525_PARAMETER_GROUPS.get(prefix.casefold())


def _parameter(
    *,
    number: int,
    code: str,
    name: str,
    description: str,
    engineering_unit: str | None = None,
    minimum: str | None = None,
    maximum: str | None = None,
    default: str | None = None,
    resolution: str | None = None,
    options: tuple[DeviceParameterOption, ...] = (),
    option_set_name: str | None = None,
    flags: tuple[DeviceParameterFlag, ...] = (),
    fields: tuple[DeviceParameterField, ...] = (),
    read_only: bool = False,
    change_requires_stop: bool = False,
    group_prefix: str = "P",
    group_name: str = "Basic Program",
) -> DeviceParameterDefinition:
    """Build a parameter definition with the common manual citation."""

    return DeviceParameterDefinition(
        number=number,
        code=code,
        name=name,
        group_prefix=group_prefix,
        group_name=group_name,
        description=description,
        engineering_unit=engineering_unit,
        minimum=minimum,
        maximum=maximum,
        default=default,
        resolution=resolution,
        options=options,
        option_set_name=option_set_name,
        flags=flags,
        fields=fields,
        read_only=read_only,
        change_requires_stop=change_requires_stop,
        reference=POWERFLEX_525_PARAMETER_REFERENCE,
    )


_START_SOURCE_OPTIONS = (
    DeviceParameterOption(value="1", label="Keypad"),
    DeviceParameterOption(value="2", label="Digital Input Terminal Block"),
    DeviceParameterOption(value="3", label="Serial/DSI"),
    DeviceParameterOption(value="4", label="Network Option"),
    DeviceParameterOption(value="5", label="EtherNet/IP"),
)

_SPEED_REFERENCE_OPTIONS = (
    DeviceParameterOption(value="1", label="Drive Potentiometer"),
    DeviceParameterOption(value="2", label="Keypad Frequency"),
    DeviceParameterOption(value="3", label="Serial/DSI"),
    DeviceParameterOption(value="4", label="Network Option"),
    DeviceParameterOption(value="5", label="0–10 V Input"),
    DeviceParameterOption(value="6", label="4–20 mA Input"),
    DeviceParameterOption(value="7", label="Preset Frequency"),
    DeviceParameterOption(value="8", label="Analog Input Multiply"),
    DeviceParameterOption(value="9", label="MOP"),
    DeviceParameterOption(value="10", label="Pulse Input"),
    DeviceParameterOption(value="11", label="PID1 Output"),
    DeviceParameterOption(value="12", label="PID2 Output"),
    DeviceParameterOption(value="13", label="Step Logic"),
    DeviceParameterOption(value="14", label="Encoder"),
    DeviceParameterOption(value="15", label="EtherNet/IP"),
    DeviceParameterOption(value="16", label="Positioning"),
)

_MOTOR_FEEDBACK_OPTIONS = (
    DeviceParameterOption(value="0", label="None"),
    DeviceParameterOption(value="1", label="Pulse Train"),
    DeviceParameterOption(value="2", label="Single Channel"),
    DeviceParameterOption(value="3", label="Single Channel with Check"),
    DeviceParameterOption(value="4", label="Quadrature"),
    DeviceParameterOption(value="5", label="Quadrature with Check"),
)

_DISABLED_ENABLED_OPTIONS = (
    DeviceParameterOption(value="0", label="Disabled"),
    DeviceParameterOption(value="1", label="Enabled"),
)

_REVERSE_DISABLE_OPTIONS = (
    DeviceParameterOption(value="0", label="Reverse Enabled"),
    DeviceParameterOption(value="1", label="Reverse Disabled"),
)

_COMPENSATION_OPTIONS = (
    DeviceParameterOption(value="0", label="Disabled"),
    DeviceParameterOption(value="1", label="Electrical"),
    DeviceParameterOption(value="2", label="Mechanical"),
    DeviceParameterOption(value="3", label="Both"),
)

_POWER_LOSS_OPTIONS = (
    DeviceParameterOption(value="0", label="Coast"),
    DeviceParameterOption(value="1", label="Decelerate"),
)

_FAULT_CLEAR_OPTIONS = (
    DeviceParameterOption(value="0", label="Ready / Idle"),
    DeviceParameterOption(value="1", label="Reset Active Fault"),
    DeviceParameterOption(value="2", label="Clear Fault Buffer"),
)

_RESET_METERS_OPTIONS = (
    DeviceParameterOption(value="0", label="Ready / Idle"),
    DeviceParameterOption(value="1", label="Reset Energy Meters"),
    DeviceParameterOption(value="2", label="Reset Time Meters"),
)

_ETHERNET_FAULT_ACTION_OPTIONS = (
    DeviceParameterOption(value="0", label="Fault"),
    DeviceParameterOption(value="1", label="Stop"),
    DeviceParameterOption(value="2", label="Zero Data"),
    DeviceParameterOption(value="3", label="Hold Last"),
    DeviceParameterOption(value="4", label="Send Fault Configuration"),
)

_DIGITAL_INPUT_OPTIONS = tuple(
    DeviceParameterOption(value=str(value), label=label)
    for value, label in (
        (0, "Not Used"),
        (1, "Speed Ref 2"),
        (2, "Speed Ref 3"),
        (3, "Start Src 2"),
        (4, "Start Src 3"),
        (5, "Spd + Strt 2"),
        (6, "Spd + Strt 3"),
        (7, "Preset Freq"),
        (8, "Jog"),
        (9, "Jog Forward"),
        (10, "Jog Reverse"),
        (11, "Acc/Dec Sel2"),
        (12, "Aux Fault"),
        (13, "Clear Fault"),
        (14, "RampStop,CF"),
        (15, "CoastStop,CF"),
        (16, "DCInjStop,CF"),
        (17, "MOP Up"),
        (18, "MOP Down"),
        (19, "Timer Start"),
        (20, "Counter In"),
        (21, "Reset Timer"),
        (22, "Reset Counter"),
        (23, "Reset Timer & Counter"),
        (24, "Logic In 1"),
        (25, "Logic In 2"),
        (26, "Current Limit 2"),
        (27, "Analog Invert"),
        (28, "EM Brake Release"),
        (29, "Acc/Dec Sel3"),
        (30, "Precharge Enable"),
        (31, "Inertia Decel"),
        (32, "Sync Enable"),
        (33, "Traverse Disable"),
        (34, "Home Limit"),
        (35, "Find Home"),
        (36, "Hold Step"),
        (37, "Position Redefine"),
        (38, "Force DC"),
        (39, "Damper Input"),
        (40, "Purge"),
        (41, "Freeze-Fire"),
        (42, "Software Enable"),
        (43, "Shear Pin 1 Disable"),
        (44, "Reserved"),
        (45, "Reserved"),
        (46, "Reserved"),
        (47, "Reserved"),
        (48, "2-Wire Forward"),
        (49, "3-Wire Start"),
        (50, "2-Wire Reverse"),
        (51, "3-Wire Direction"),
        (52, "Pulse Train"),
    )
)

_TWO_WIRE_MODE_OPTIONS = (
    DeviceParameterOption(value="0", label="Edge Trigger"),
    DeviceParameterOption(value="1", label="Level Sense"),
    DeviceParameterOption(value="2", label="High-Speed Edge"),
    DeviceParameterOption(value="3", label="Momentary"),
)

_DIGITAL_OUTPUT_OPTIONS = tuple(
    DeviceParameterOption(value=str(value), label=label)
    for value, label in (
        (0, "Ready/Fault"),
        (1, "At Frequency"),
        (2, "Motor Running"),
        (3, "Reverse"),
        (4, "Motor Overload"),
        (5, "Ramp Regulator"),
        (6, "Above Frequency"),
        (7, "Above Current"),
        (8, "Above DC Voltage"),
        (9, "Retries Exhausted"),
        (10, "Above Analog Voltage"),
        (11, "Above Power Factor Angle"),
        (12, "Analog Input Loss"),
        (13, "Parameter Control"),
        (14, "Non-Resettable Fault"),
        (15, "EM Brake Control"),
        (16, "Thermal Overload"),
        (17, "Ambient Overtemperature"),
        (18, "Local Active"),
        (19, "Communication Loss"),
        (20, "Logic Input 1"),
        (21, "Logic Input 2"),
        (22, "Logic 1 AND 2"),
        (23, "Logic 1 OR 2"),
        (24, "StepLogic Output"),
        (25, "Timer Output"),
        (26, "Counter Output"),
        (27, "At Position"),
        (28, "At Home"),
        (29, "Safe-Off"),
        (30, "Safe Torque Permit"),
        (31, "Auto-Restart Countdown"),
    )
)

_OPTO_OUTPUT_LOGIC_OPTIONS = (
    DeviceParameterOption(value="0", label="Output 1 NO; Output 2 NO"),
    DeviceParameterOption(value="1", label="Output 1 NC; Output 2 NO"),
    DeviceParameterOption(value="2", label="Output 1 NO; Output 2 NC"),
    DeviceParameterOption(value="3", label="Output 1 NC; Output 2 NC"),
)

_ANALOG_OUTPUT_OPTIONS = tuple(
    DeviceParameterOption(value=str(value), label=label)
    for value, label in (
        (0, "Output Frequency 0–10 V"),
        (1, "Output Current 0–10 V"),
        (2, "Output Voltage 0–10 V"),
        (3, "Output Power 0–10 V"),
        (4, "Output Torque 0–10 V"),
        (5, "Test Data 0–10 V"),
        (6, "Setpoint 0–10 V"),
        (7, "DC Bus Voltage 0–10 V"),
        (8, "Output Frequency 0–20 mA"),
        (9, "Output Current 0–20 mA"),
        (10, "Output Voltage 0–20 mA"),
        (11, "Output Power 0–20 mA"),
        (12, "Output Torque 0–20 mA"),
        (13, "Test Data 0–20 mA"),
        (14, "Setpoint 0–20 mA"),
        (15, "DC Bus Voltage 0–20 mA"),
        (16, "Output Frequency 4–20 mA"),
        (17, "Output Current 4–20 mA"),
        (18, "Output Voltage 4–20 mA"),
        (19, "Output Power 4–20 mA"),
        (20, "Output Torque 4–20 mA"),
        (21, "Test Data 4–20 mA"),
        (22, "Setpoint 4–20 mA"),
        (23, "DC Bus Voltage 4–20 mA"),
    )
)

_SAFETY_OPEN_OPTIONS = (
    DeviceParameterOption(value="0", label="Fault Enable"),
    DeviceParameterOption(value="1", label="Fault Disable"),
)

_SAFETY_FAULT_RESET_OPTIONS = (
    DeviceParameterOption(value="0", label="Power-Cycle Reset"),
    DeviceParameterOption(value="1", label="Fault-Clear Reset"),
)

_CONTROL_SOURCE_START_OPTIONS = _START_SOURCE_OPTIONS

_CONTROL_SOURCE_FREQUENCY_OPTIONS = (
    DeviceParameterOption(value="00", label="Other"),
    *(
        DeviceParameterOption(value=f"{int(option.value):02d}", label=option.label)
        for option in _SPEED_REFERENCE_OPTIONS
    ),
)

_CONTROL_SOURCE_OVERRIDE_OPTIONS = (
    DeviceParameterOption(value="0", label="Other"),
    DeviceParameterOption(value="1", label="Jog"),
    DeviceParameterOption(value="2", label="Purge"),
)


def _digital_input_parameter(
    number: int,
    terminal: str,
    default: str,
) -> DeviceParameterDefinition:
    """Build one terminal-specific programmable digital-input definition."""

    return _parameter(
        number=number,
        code=f"T{number:03d}",
        name=f"DigIn TermBlk {terminal}",
        description=(
            f"Assigns the function of digital input terminal {terminal}; "
            "some choices are terminal-specific or may be assigned to only "
            "one input."
        ),
        default=default,
        options=_DIGITAL_INPUT_OPTIONS,
        option_set_name="Programmable Digital Input",
        change_requires_stop=True,
        group_prefix="T",
        group_name="Terminal Block",
    )


def _opto_output_selection_parameter(
    number: int,
    output: int,
    default: str,
) -> DeviceParameterDefinition:
    """Build one programmable opto-output selection definition."""

    return _parameter(
        number=number,
        code=f"T{number:03d}",
        name=f"Opto Out{output} Sel",
        description=(
            f"Selects the condition that changes opto output {output} state."
        ),
        default=default,
        options=_DIGITAL_OUTPUT_OPTIONS,
        option_set_name="Programmable Digital Output",
        group_prefix="T",
        group_name="Terminal Block",
    )


def _opto_output_level_parameter(
    number: int,
    output: int,
    selection_parameter: str,
) -> DeviceParameterDefinition:
    """Build a level whose meaning depends on its output selection."""

    return _parameter(
        number=number,
        code=f"T{number:03d}",
        name=f"Opto Out{output} Level",
        description=(
            f"Sets the opto output {output} switching threshold or direct "
            f"control value; its units and valid range depend on "
            f"{selection_parameter}."
        ),
        minimum="0.0",
        maximum="9999.0",
        default="0.0",
        resolution="0.1",
        group_prefix="T",
        group_name="Terminal Block",
    )


def _relay_output_selection_parameter(
    number: int,
    relay: int,
    default: str,
) -> DeviceParameterDefinition:
    """Build one programmable relay-output selection definition."""

    return _parameter(
        number=number,
        code=f"T{number:03d}",
        name=f"Relay Out{relay} Sel",
        description=(
            f"Selects the condition that changes relay output {relay} state."
        ),
        default=default,
        options=_DIGITAL_OUTPUT_OPTIONS,
        option_set_name="Programmable Digital Output",
        group_prefix="T",
        group_name="Terminal Block",
    )


def _relay_output_level_parameter(
    number: int,
    relay: int,
    selection_parameter: str,
) -> DeviceParameterDefinition:
    """Build a relay level whose meaning depends on its selection."""

    return _parameter(
        number=number,
        code=f"T{number:03d}",
        name=f"Relay Out{relay} Level",
        description=(
            f"Sets the relay output {relay} switching threshold or direct "
            f"control value; its units and valid range depend on "
            f"{selection_parameter}."
        ),
        minimum="0.0",
        maximum="9999.0",
        default="0.0",
        resolution="0.1",
        group_prefix="T",
        group_name="Terminal Block",
    )


def _relay_delay_parameter(
    number: int,
    relay: int,
    transition: str,
) -> DeviceParameterDefinition:
    """Build one relay energize or de-energize delay definition."""

    action = "energizes" if transition == "On" else "de-energizes"
    condition = "is met" if transition == "On" else "ceases"
    return _parameter(
        number=number,
        code=f"T{number:03d}",
        name=f"Relay {relay} {transition} Time",
        description=(
            f"Sets the delay before relay {relay} {action} after its "
            f"selected condition {condition}."
        ),
        engineering_unit="s",
        minimum="0.0",
        maximum="600.0",
        default="0.0",
        resolution="0.1 s",
        group_prefix="T",
        group_name="Terminal Block",
    )


def _basic_display_parameter(
    *,
    number: int,
    name: str,
    description: str,
    engineering_unit: str | None = None,
    minimum: str | None = None,
    maximum: str | None = None,
    resolution: str | None = None,
    flags: tuple[DeviceParameterFlag, ...] = (),
    fields: tuple[DeviceParameterField, ...] = (),
) -> DeviceParameterDefinition:
    """Build one read-only Basic Display definition."""

    return _parameter(
        number=number,
        code=f"b{number:03d}",
        name=name,
        description=description,
        engineering_unit=engineering_unit,
        minimum=minimum,
        maximum=maximum,
        resolution=resolution,
        flags=flags,
        fields=fields,
        read_only=True,
        group_prefix="b",
        group_name="Basic Display",
    )


def _advanced_display_parameter(
    *,
    number: int,
    name: str,
    description: str,
    engineering_unit: str | None = None,
    minimum: str | None = None,
    maximum: str | None = None,
    resolution: str | None = None,
    flags: tuple[DeviceParameterFlag, ...] = (),
) -> DeviceParameterDefinition:
    """Build one read-only Advanced Display definition."""

    return _parameter(
        number=number,
        code=f"d{number:03d}",
        name=name,
        description=description,
        engineering_unit=engineering_unit,
        minimum=minimum,
        maximum=maximum,
        resolution=resolution,
        flags=flags,
        read_only=True,
        group_prefix="d",
        group_name="Advanced Display",
    )


def _advanced_program_parameter(
    *,
    number: int,
    name: str,
    description: str,
    engineering_unit: str | None = None,
    minimum: str | None = None,
    maximum: str | None = None,
    default: str | None = None,
    resolution: str | None = None,
    options: tuple[DeviceParameterOption, ...] = (),
    option_set_name: str | None = None,
    change_requires_stop: bool,
) -> DeviceParameterDefinition:
    """Build one writable Advanced Program definition."""

    return _parameter(
        number=number,
        code=f"A{number:03d}",
        name=name,
        description=description,
        engineering_unit=engineering_unit,
        minimum=minimum,
        maximum=maximum,
        default=default,
        resolution=resolution,
        options=options,
        option_set_name=option_set_name,
        change_requires_stop=change_requires_stop,
        group_prefix="A",
        group_name="Advanced Program",
    )


def _fault_diagnostic_parameter(
    *,
    number: int,
    name: str,
    description: str,
    engineering_unit: str | None = None,
    minimum: str | None = None,
    maximum: str | None = None,
    resolution: str | None = None,
) -> DeviceParameterDefinition:
    """Build one read-only Fault and Diagnostic definition."""

    return _parameter(
        number=number,
        code=f"F{number:03d}",
        name=name,
        description=description,
        engineering_unit=engineering_unit,
        minimum=minimum,
        maximum=maximum,
        resolution=resolution,
        read_only=True,
        group_prefix="F",
        group_name="Fault and Diagnostic",
    )


def _historical_fault_code_parameter(
    number: int,
    history_position: int,
) -> DeviceParameterDefinition:
    """Build one entry in the drive's unique recent-fault history."""

    return _fault_diagnostic_parameter(
        number=number,
        name=f"Fault {history_position} Code",
        description=(
            f"Reports entry {history_position} in the unique recent-fault "
            "history, where entry 1 is the most recent."
        ),
        minimum="F0",
        maximum="F127",
    )


def _historical_fault_frequency_parameter(
    number: int,
    history_position: int,
) -> DeviceParameterDefinition:
    """Build an output-frequency snapshot for one recent fault."""

    return _fault_diagnostic_parameter(
        number=number,
        name=f"Fault {history_position} Frequency",
        description=(
            "Stores the output frequency recorded with fault-history entry "
            f"{history_position}, where entry 1 is the most recent."
        ),
        engineering_unit="Hz",
        minimum="0.00",
        maximum="500.00",
        resolution="0.01 Hz",
    )


def _historical_fault_current_parameter(
    number: int,
    history_position: int,
) -> DeviceParameterDefinition:
    """Build an output-current snapshot for one recent fault."""

    return _fault_diagnostic_parameter(
        number=number,
        name=f"Fault {history_position} Current",
        description=(
            "Stores the output current recorded with fault-history entry "
            f"{history_position}, where entry 1 is the most recent."
        ),
        engineering_unit="A",
        minimum="0.00",
        maximum="Drive Rated Amps x 2",
        resolution="0.01 A",
    )


def _historical_fault_bus_voltage_parameter(
    number: int,
    history_position: int,
) -> DeviceParameterDefinition:
    """Build a DC-bus-voltage snapshot for one recent fault."""

    return _fault_diagnostic_parameter(
        number=number,
        name=f"Fault {history_position} DC Bus Voltage",
        description=(
            "Stores the DC bus voltage recorded with fault-history entry "
            f"{history_position}, where entry 1 is the most recent."
        ),
        engineering_unit="V DC",
        minimum="0",
        maximum="1200",
        resolution="1 V DC",
    )


def _active_network_octet_parameter(
    *,
    number: int,
    address_kind: str,
    octet: int,
) -> DeviceParameterDefinition:
    """Build one active embedded EtherNet/IP address octet."""

    return _fault_diagnostic_parameter(
        number=number,
        name=f"Active {address_kind} Octet {octet}",
        description=(
            f"Reports octet {octet} of the active {address_kind.lower()} "
            "currently used by the embedded EtherNet/IP interface; a value "
            "of zero can indicate that no address is set."
        ),
        minimum="0",
        maximum="255",
        resolution="1",
    )


def _fault_code_parameter(number: int, sequence: str) -> DeviceParameterDefinition:
    """Build one ordered recent-fault code definition."""

    ordinal = {"1": "first", "2": "second", "3": "third"}[sequence]
    return _basic_display_parameter(
        number=number,
        name=f"Fault {sequence} Code",
        description=(
            f"Reports the {ordinal} entry in the unique recent-fault "
            "history, with Fault 1 being the most recent."
        ),
        minimum="F0",
        maximum="F127",
    )


_PARAMETERS = {
    1: _basic_display_parameter(
        number=1,
        name="Output Freq",
        description=(
            "Reports output frequency at motor terminals T1, T2, and T3, "
            "excluding slip frequency."
        ),
        engineering_unit="Hz",
        minimum="0.00",
        maximum="P044 Maximum Freq",
        resolution="0.01 Hz",
    ),
    2: _basic_display_parameter(
        number=2,
        name="Commanded Freq",
        description=(
            "Reports the active frequency command whether or not the drive "
            "is running."
        ),
        engineering_unit="Hz",
        minimum="0.00",
        maximum="P044 Maximum Freq",
        resolution="0.01 Hz",
    ),
    3: _basic_display_parameter(
        number=3,
        name="Output Current",
        description="Reports output current at motor terminals T1, T2, and T3.",
        engineering_unit="A",
        minimum="0.00",
        maximum="Drive Rated Amps × 2",
        resolution="0.01 A",
    ),
    4: _basic_display_parameter(
        number=4,
        name="Output Voltage",
        description="Reports output voltage at motor terminals T1, T2, and T3.",
        engineering_unit="V",
        minimum="0.0",
        maximum="Drive Rated Volts",
        resolution="0.1 V",
    ),
    5: _basic_display_parameter(
        number=5,
        name="DC Bus Voltage",
        description="Reports the filtered drive DC-bus voltage.",
        engineering_unit="V DC",
        minimum="0",
        maximum="1200",
        resolution="1 V DC",
    ),
    6: _basic_display_parameter(
        number=6,
        name="Drive Status",
        description=(
            "Reports the present drive operating condition as active flags."
        ),
        minimum="00000",
        maximum="11111",
        flags=(
            DeviceParameterFlag(position="Digit 1", label="Running"),
            DeviceParameterFlag(position="Digit 2", label="Forward"),
            DeviceParameterFlag(position="Digit 3", label="Accelerating"),
            DeviceParameterFlag(position="Digit 4", label="Decelerating"),
            DeviceParameterFlag(position="Digit 5", label="Safety Active"),
        ),
    ),
    7: _fault_code_parameter(7, "1"),
    8: _fault_code_parameter(8, "2"),
    9: _fault_code_parameter(9, "3"),
    12: _basic_display_parameter(
        number=12,
        name="Control Source",
        description=(
            "Reports the active start-command and frequency-command sources "
            "as encoded decimal digits."
        ),
        minimum="0000",
        maximum="2165",
        fields=(
            DeviceParameterField(
                position="Digit 1",
                label="Start command source",
                options=_CONTROL_SOURCE_START_OPTIONS,
            ),
            DeviceParameterField(
                position="Digits 2–3",
                label="Frequency command source",
                options=_CONTROL_SOURCE_FREQUENCY_OPTIONS,
            ),
            DeviceParameterField(
                position="Digit 4",
                label="Frequency override",
                options=_CONTROL_SOURCE_OVERRIDE_OPTIONS,
            ),
        ),
    ),
    13: _basic_display_parameter(
        number=13,
        name="Control Input Status",
        description=(
            "Reports terminal-block inputs 1 through 3 and the dynamic-brake "
            "transistor state."
        ),
        minimum="0000",
        maximum="1111",
        flags=(
            DeviceParameterFlag(position="Digit 1", label="Terminal 1 Closed"),
            DeviceParameterFlag(position="Digit 2", label="Terminal 2 Closed"),
            DeviceParameterFlag(position="Digit 3", label="Terminal 3 Closed"),
            DeviceParameterFlag(
                position="Digit 4",
                label="Dynamic-Brake Transistor On",
            ),
        ),
    ),
    14: _basic_display_parameter(
        number=14,
        name="Digital Input Status",
        description="Reports the state of programmable digital inputs 5–8.",
        minimum="0000",
        maximum="1111",
        flags=(
            DeviceParameterFlag(position="Digit 1", label="Terminal 5 Closed"),
            DeviceParameterFlag(position="Digit 2", label="Terminal 6 Closed"),
            DeviceParameterFlag(position="Digit 3", label="Terminal 7 Closed"),
            DeviceParameterFlag(position="Digit 4", label="Terminal 8 Closed"),
        ),
    ),
    15: _basic_display_parameter(
        number=15,
        name="Output RPM",
        description=(
            "Reports output frequency converted to rotational speed using "
            "P035 Motor NP Poles."
        ),
        engineering_unit="rpm",
        minimum="0",
        maximum="24000",
        resolution="1 rpm",
    ),
    16: _basic_display_parameter(
        number=16,
        name="Output Speed",
        description=(
            "Reports output frequency as a percentage of P044 Maximum Freq."
        ),
        engineering_unit="%",
        minimum="0.0",
        maximum="100.0",
        resolution="0.1%",
    ),
    17: _basic_display_parameter(
        number=17,
        name="Output Power",
        description="Reports output power at motor terminals T1, T2, and T3.",
        engineering_unit="kW",
        minimum="0.00",
        maximum="Drive Rated Power × 2",
        resolution="0.01 kW",
    ),
    19: _basic_display_parameter(
        number=19,
        name="Elapsed Run Time",
        description=(
            "Reports accumulated time during which the drive has been "
            "outputting power."
        ),
        engineering_unit="h",
        minimum="0",
        maximum="65535 × 10",
        resolution="10 h",
    ),
    20: _basic_display_parameter(
        number=20,
        name="Average Power",
        description=(
            "Reports average motor power since the energy meters were last "
            "reset."
        ),
        engineering_unit="kW",
        minimum="0.00",
        maximum="Drive Rated Power × 2",
        resolution="0.01 kW",
    ),
    21: _basic_display_parameter(
        number=21,
        name="Elapsed kWh",
        description=(
            "Reports accumulated output energy; at 100.0 kWh it resets and "
            "increments b022 Elapsed MWh."
        ),
        engineering_unit="kWh",
        minimum="0.0",
        maximum="100.0",
        resolution="0.1 kWh",
    ),
    22: _basic_display_parameter(
        number=22,
        name="Elapsed MWh",
        description="Reports accumulated drive output energy in megawatt-hours.",
        engineering_unit="MWh",
        minimum="0.0",
        maximum="6553.5",
        resolution="0.1 MWh",
    ),
    27: _basic_display_parameter(
        number=27,
        name="Drive Temp",
        description=(
            "Reports the present operating temperature of the drive heatsink."
        ),
        engineering_unit="°C",
        minimum="0",
        maximum="120",
        resolution="1 °C",
    ),
    28: _basic_display_parameter(
        number=28,
        name="Control Temp",
        description=(
            "Reports the present operating temperature of the drive control."
        ),
        engineering_unit="°C",
        minimum="0",
        maximum="120",
        resolution="1 °C",
    ),
    29: _basic_display_parameter(
        number=29,
        name="Control SW Version",
        description="Reports the current drive firmware revision.",
        minimum="0.000",
        maximum="65.535",
        resolution="0.001",
    ),
    31: _parameter(
        number=31,
        code="P031",
        name="Motor NP Volts",
        description="Sets the motor nameplate rated voltage.",
        engineering_unit="V",
        minimum=(
            "10 (230 V drives), 20 (460 V drives), "
            "or 25 (600 V drives)"
        ),
        maximum="Drive Rated Volts",
        default="Drive Rated Volts",
        resolution="1 V",
        change_requires_stop=True,
    ),
    32: _parameter(
        number=32,
        code="P032",
        name="Motor NP Hertz",
        description="Sets the motor nameplate rated frequency.",
        engineering_unit="Hz",
        minimum="15",
        maximum="500",
        default="60",
        resolution="1 Hz",
        change_requires_stop=True,
    ),
    33: _parameter(
        number=33,
        code="P033",
        name="Motor OL Current",
        description=(
            "Sets the motor nameplate overload current used to determine "
            "motor overload conditions."
        ),
        engineering_unit="A",
        minimum="0.0",
        maximum="Drive Rated Amps × 2",
        default="Drive Rated Amps",
        resolution="0.1 A",
    ),
    34: _parameter(
        number=34,
        code="P034",
        name="Motor NP FLA",
        description=(
            "Sets the motor nameplate full-load current used by autotune "
            "and motor control."
        ),
        engineering_unit="A",
        minimum="0.1",
        maximum="Drive Rated Amps × 2",
        default="Based on Drive Rating",
        resolution="0.1 A",
    ),
    35: _parameter(
        number=35,
        code="P035",
        name="Motor NP Poles",
        description="Sets the number of poles in the motor.",
        minimum="2",
        maximum="40",
        default="4",
        resolution="1",
    ),
    36: _parameter(
        number=36,
        code="P036",
        name="Motor NP RPM",
        description=(
            "Sets the rated motor nameplate speed used to calculate "
            "rated slip."
        ),
        engineering_unit="rpm",
        minimum="0",
        maximum="24000",
        default="1750",
        resolution="1 rpm",
        change_requires_stop=True,
    ),
    37: _parameter(
        number=37,
        code="P037",
        name="Motor NP Power",
        description="Sets the motor nameplate power used by the PM regulator.",
        engineering_unit="kW",
        minimum="0.00",
        maximum="Drive Rated Power",
        default="Drive Rated Power",
        resolution="0.01 kW",
    ),
    38: _parameter(
        number=38,
        code="P038",
        name="Voltage Class",
        description="Sets the voltage class of 600 V drives.",
        default="3",
        options=(
            DeviceParameterOption(value="2", label="Low Voltage (480 V)"),
            DeviceParameterOption(value="3", label="High Voltage (600 V)"),
        ),
        change_requires_stop=True,
    ),
    39: _parameter(
        number=39,
        code="P039",
        name="Torque Perf Mode",
        description="Selects the motor control mode.",
        default="1",
        options=(
            DeviceParameterOption(value="0", label="V/Hz"),
            DeviceParameterOption(value="1", label="SVC"),
            DeviceParameterOption(value="2", label="Economize"),
            DeviceParameterOption(value="3", label="Vector"),
            DeviceParameterOption(value="4", label="PM Control"),
            DeviceParameterOption(value="5", label="SynRM"),
        ),
        change_requires_stop=True,
    ),
    40: _parameter(
        number=40,
        code="P040",
        name="Autotune",
        description=(
            "Initiates a static or rotational autotune and returns to "
            "Ready/Idle when complete."
        ),
        default="0",
        options=(
            DeviceParameterOption(value="0", label="Ready/Idle"),
            DeviceParameterOption(value="1", label="Static Tune"),
            DeviceParameterOption(value="2", label="Rotate Tune"),
        ),
        change_requires_stop=True,
    ),
    41: _parameter(
        number=41,
        code="P041",
        name="Accel Time 1",
        description=(
            "Sets the time to accelerate from 0 Hz to P044 Maximum Freq."
        ),
        engineering_unit="s",
        minimum="0.00",
        maximum="600.00",
        default="10.00",
        resolution="0.01 s",
    ),
    42: _parameter(
        number=42,
        code="P042",
        name="Decel Time 1",
        description=(
            "Sets the time to decelerate from P044 Maximum Freq to 0 Hz."
        ),
        engineering_unit="s",
        minimum="0.00",
        maximum="600.00",
        default="10.00",
        resolution="0.01 s",
    ),
    43: _parameter(
        number=43,
        code="P043",
        name="Minimum Freq",
        description="Sets the lowest frequency the drive outputs.",
        engineering_unit="Hz",
        minimum="0.00",
        maximum="500.00",
        default="0.00",
        resolution="0.01 Hz",
        change_requires_stop=True,
    ),
    44: _parameter(
        number=44,
        code="P044",
        name="Maximum Freq",
        description="Sets the highest frequency the drive outputs.",
        engineering_unit="Hz",
        minimum="0.00",
        maximum="500.00",
        default="60.00",
        resolution="0.01 Hz",
        change_requires_stop=True,
    ),
    45: _parameter(
        number=45,
        code="P045",
        name="Stop Mode",
        description="Selects the stopping mode used when a stop is initiated.",
        default="0",
        options=(
            DeviceParameterOption(value="0", label="Ramp, CF"),
            DeviceParameterOption(value="1", label="Coast, CF"),
            DeviceParameterOption(value="2", label="DC Brake, CF"),
            DeviceParameterOption(value="3", label="DC BrkAuto,CF"),
            DeviceParameterOption(value="4", label="Ramp"),
            DeviceParameterOption(value="5", label="Coast"),
            DeviceParameterOption(value="6", label="DC Brake"),
            DeviceParameterOption(value="7", label="DC BrakeAuto"),
            DeviceParameterOption(value="8", label="Ramp+EM B,CF"),
            DeviceParameterOption(value="9", label="Ramp+EM Brk"),
            DeviceParameterOption(value="10", label="PointStp,CF"),
            DeviceParameterOption(value="11", label="PointStop"),
        ),
    ),
    46: _parameter(
        number=46,
        code="P046",
        name="Start Source 1",
        description="Selects the primary start-command source.",
        default="1",
        options=_START_SOURCE_OPTIONS,
        option_set_name="Start Source",
        change_requires_stop=True,
    ),
    47: _parameter(
        number=47,
        code="P047",
        name="Speed Reference 1",
        description="Selects the primary speed-command source.",
        default="1",
        options=_SPEED_REFERENCE_OPTIONS,
        option_set_name="Speed Reference",
    ),
    48: _parameter(
        number=48,
        code="P048",
        name="Start Source 2",
        description="Selects the second start-command source.",
        default="2",
        options=_START_SOURCE_OPTIONS,
        option_set_name="Start Source",
        change_requires_stop=True,
    ),
    49: _parameter(
        number=49,
        code="P049",
        name="Speed Reference 2",
        description="Selects the second speed-command source.",
        default="5",
        options=_SPEED_REFERENCE_OPTIONS,
        option_set_name="Speed Reference",
    ),
    50: _parameter(
        number=50,
        code="P050",
        name="Start Source 3",
        description="Selects the third start-command source.",
        default="5",
        options=_START_SOURCE_OPTIONS,
        option_set_name="Start Source",
        change_requires_stop=True,
    ),
    51: _parameter(
        number=51,
        code="P051",
        name="Speed Reference 3",
        description="Selects the third speed-command source.",
        default="15",
        options=_SPEED_REFERENCE_OPTIONS,
        option_set_name="Speed Reference",
    ),
    53: _parameter(
        number=53,
        code="P053",
        name="Reset To Defaults",
        description=(
            "Issues a parameter, factory, power-parameter, or module reset "
            "and then returns to Ready/Idle."
        ),
        default="0",
        options=(
            DeviceParameterOption(value="0", label="Ready/Idle"),
            DeviceParameterOption(value="1", label="Param Reset"),
            DeviceParameterOption(value="2", label="Factory Reset"),
            DeviceParameterOption(value="3", label="Power Reset"),
            DeviceParameterOption(value="4", label="Module Reset"),
        ),
        change_requires_stop=True,
    ),
    62: _digital_input_parameter(62, "02", "48"),
    63: _digital_input_parameter(63, "03", "50"),
    64: _parameter(
        number=64,
        code="T064",
        name="2-Wire Mode",
        description=(
            "Selects the trigger mode for terminals 02 and 03 when a "
            "two-wire start source is used. Level Sense can restart when a "
            "maintained Run input remains active."
        ),
        default="0",
        options=_TWO_WIRE_MODE_OPTIONS,
        change_requires_stop=True,
        group_prefix="T",
        group_name="Terminal Block",
    ),
    65: _digital_input_parameter(65, "05", "7"),
    66: _digital_input_parameter(66, "06", "7"),
    67: _digital_input_parameter(67, "07", "5"),
    68: _digital_input_parameter(68, "08", "9"),
    69: _opto_output_selection_parameter(69, 1, "2"),
    70: _opto_output_level_parameter(70, 1, "T069"),
    72: _opto_output_selection_parameter(72, 2, "1"),
    73: _opto_output_level_parameter(73, 2, "T072"),
    75: _parameter(
        number=75,
        code="T075",
        name="Opto Out Logic",
        description=(
            "Selects normally-open or normally-closed logic independently "
            "for the two opto outputs."
        ),
        default="0",
        options=_OPTO_OUTPUT_LOGIC_OPTIONS,
        group_prefix="T",
        group_name="Terminal Block",
    ),
    76: _relay_output_selection_parameter(76, 1, "0"),
    77: _relay_output_level_parameter(77, 1, "T076"),
    79: _relay_delay_parameter(79, 1, "On"),
    80: _relay_delay_parameter(80, 1, "Off"),
    81: _relay_output_selection_parameter(81, 2, "2"),
    82: _relay_output_level_parameter(82, 2, "T081"),
    84: _relay_delay_parameter(84, 2, "On"),
    85: _relay_delay_parameter(85, 2, "Off"),
    88: _parameter(
        number=88,
        code="T088",
        name="Analog Out Sel",
        description=(
            "Selects the drive quantity and electrical range represented by "
            "the analog output."
        ),
        default="0",
        options=_ANALOG_OUTPUT_OPTIONS,
        option_set_name="Analog Output Selection",
        group_prefix="T",
        group_name="Terminal Block",
    ),
    90: _parameter(
        number=90,
        code="T090",
        name="Analog Out Setpoint",
        description=(
            "Sets the requested analog-output percentage when T088 selects "
            "setpoint mode 6, 14, or 22."
        ),
        engineering_unit="%",
        minimum="0.0",
        maximum="100.0",
        default="0.0",
        resolution="0.1%",
        group_prefix="T",
        group_name="Terminal Block",
    ),
    99: _parameter(
        number=99,
        code="T099",
        name="Analog In Filter",
        description=(
            "Selects additional analog-input filtering; each increment "
            "doubles the applied filtering and reduces bandwidth."
        ),
        minimum="0",
        maximum="14",
        default="0",
        resolution="1",
        group_prefix="T",
        group_name="Terminal Block",
    ),
    105: _parameter(
        number=105,
        code="T105",
        name="Safety Open Enable",
        description=(
            "Selects whether the drive faults when both safe-torque-off "
            "inputs are de-energized."
        ),
        default="0",
        options=_SAFETY_OPEN_OPTIONS,
        group_prefix="T",
        group_name="Terminal Block",
    ),
    106: _parameter(
        number=106,
        code="T106",
        name="Safety Fault Reset Configuration",
        description=(
            "Selects whether safety hardware fault F111 is reset by a power "
            "cycle or by the fault-clear mechanism."
        ),
        default="0",
        options=_SAFETY_FAULT_RESET_OPTIONS,
        group_prefix="T",
        group_name="Terminal Block",
    ),
    143: _parameter(
        number=143,
        code="C143",
        name="EN Comm Flt Actn",
        description=(
            "Selects the drive action when embedded EtherNet/IP "
            "communications are disrupted. Non-fault selections can permit "
            "continued operation and require commissioning verification."
        ),
        default="0",
        options=_ETHERNET_FAULT_ACTION_OPTIONS,
        option_set_name="EtherNet/IP Fault Action",
        group_prefix="C",
        group_name="Communications",
    ),
    144: _parameter(
        number=144,
        code="C144",
        name="EN Idle Flt Actn",
        description=(
            "Selects the drive action when the EtherNet/IP scanner becomes "
            "idle because the controller enters Program mode. Non-fault "
            "selections can permit continued operation and require "
            "commissioning verification."
        ),
        default="0",
        options=_ETHERNET_FAULT_ACTION_OPTIONS,
        option_set_name="EtherNet/IP Fault Action",
        group_prefix="C",
        group_name="Communications",
    ),
    360: _advanced_display_parameter(
        number=360,
        name="Analog In 0-10V",
        description=(
            "Reports the 0-10 V analog input as a percentage of full scale."
        ),
        engineering_unit="%",
        minimum="0.0",
        maximum="100.0",
        resolution="0.1%",
    ),
    361: _advanced_display_parameter(
        number=361,
        name="Analog In 4-20mA",
        description=(
            "Reports the 4-20 mA analog input as a percentage of full scale."
        ),
        engineering_unit="%",
        minimum="0.0",
        maximum="100.0",
        resolution="0.1%",
    ),
    362: _advanced_display_parameter(
        number=362,
        name="Elapsed Time-hr",
        description=(
            "Reports total powered-up hours since the elapsed-time meter was "
            "reset; unlike b019, this is not limited to time outputting power."
        ),
        engineering_unit="h",
        minimum="0",
        maximum="32767",
        resolution="1 h",
    ),
    363: _advanced_display_parameter(
        number=363,
        name="Elapsed Time-min",
        description=(
            "Reports the minute component of total powered-up time; at its "
            "maximum it resets to zero and increments d362 by one hour."
        ),
        engineering_unit="min",
        minimum="0.0",
        maximum="60.0",
        resolution="0.1 min",
    ),
    364: _advanced_display_parameter(
        number=364,
        name="Counter Status",
        description=(
            "Reports the current accumulated value of the internal counter "
            "when the counter function is enabled."
        ),
        minimum="0",
        maximum="65535",
        resolution="1",
    ),
    367: _advanced_display_parameter(
        number=367,
        name="Drive Type",
        description=(
            "Reports the internal drive-type setting used by Rockwell "
            "Automation field service personnel."
        ),
        minimum="0",
        maximum="65535",
        resolution="1",
    ),
    369: _advanced_display_parameter(
        number=369,
        name="Motor OL Level",
        description="Reports the present value of the motor overload counter.",
        engineering_unit="%",
        minimum="0.0",
        maximum="150.0",
        resolution="0.1%",
    ),
    375: _advanced_display_parameter(
        number=375,
        name="Slip Hz Meter",
        description=(
            "Reports the absolute amount of slip or droop presently applied "
            "to motor frequency."
        ),
        engineering_unit="Hz",
        minimum="0.0",
        maximum="25.0",
        resolution="0.1 Hz",
    ),
    376: _advanced_display_parameter(
        number=376,
        name="Speed Feedback",
        description=(
            "Reports actual motor speed, measured by the feedback device "
            "when selected or otherwise estimated by the drive."
        ),
        engineering_unit="rpm",
        minimum="0.0",
        maximum="64000.0",
        resolution="0.1 rpm",
    ),
    378: _advanced_display_parameter(
        number=378,
        name="Encoder Speed",
        description=(
            "Reports speed measured by the encoder or pulse-train feedback "
            "device, even when it is not controlling motor speed."
        ),
        engineering_unit="rpm",
        minimum="0.0",
        maximum="64000.0",
        resolution="0.1 rpm",
    ),
    380: _advanced_display_parameter(
        number=380,
        name="DC Bus Ripple",
        description="Reports the real-time DC-bus ripple voltage.",
        engineering_unit="V DC",
        minimum="0",
        maximum=(
            "410 (230 V AC drive), 820 (460 V AC drive), or "
            "1025 (600 V AC drive)"
        ),
        resolution="1 V DC",
    ),
    381: _advanced_display_parameter(
        number=381,
        name="Output Powr Fctr",
        description=(
            "Reports the electrical angle between motor voltage and motor "
            "current."
        ),
        engineering_unit="°",
        minimum="0.0",
        maximum="180.0",
        resolution="0.1°",
    ),
    382: _advanced_display_parameter(
        number=382,
        name="Torque Current",
        description="Reports motor torque current measured by the drive.",
        engineering_unit="A",
        minimum="0.00",
        maximum="Drive Rated Amps × 2",
        resolution="0.01 A",
    ),
    393: _advanced_display_parameter(
        number=393,
        name="Drive Status 2",
        description=(
            "Reports the present operating condition of the drive as a "
            "bit-mapped status word."
        ),
        minimum="0",
        maximum="65535",
        resolution="1",
        flags=(
            DeviceParameterFlag("0", "Jogging"),
            DeviceParameterFlag("1", "Flux Braking"),
            DeviceParameterFlag("2", "Motor Overload"),
            DeviceParameterFlag("3", "Auto-reset Countdown"),
            DeviceParameterFlag("4", "DC Braking"),
            DeviceParameterFlag("5", "At Frequency"),
            DeviceParameterFlag("6", "Auto-tuning"),
            DeviceParameterFlag("7", "EM Braking"),
            DeviceParameterFlag("8", "Current Limiting"),
            DeviceParameterFlag("10", "Safety Input 1"),
            DeviceParameterFlag("11", "Safety Input 2"),
            DeviceParameterFlag("12", "Fault 111 Status"),
            DeviceParameterFlag("13", "Safe Torque Permit"),
        ),
    ),
    394: _advanced_display_parameter(
        number=394,
        name="Dig Out Status",
        description=(
            "Reports the activation states of relay and opto-isolated outputs "
            "as a bit-mapped status word."
        ),
        minimum="0",
        maximum="15",
        resolution="1",
        flags=(
            DeviceParameterFlag("0", "Relay Output 1"),
            DeviceParameterFlag("1", "Relay Output 2"),
            DeviceParameterFlag("2", "Opto Output 1"),
            DeviceParameterFlag("3", "Opto Output 2"),
        ),
    ),
    431: _advanced_program_parameter(
        number=431,
        name="Jog Frequency",
        description="Sets output frequency while a jog command is active.",
        engineering_unit="Hz",
        minimum="0.00",
        maximum="P044 Maximum Freq",
        default="10.00",
        resolution="0.01 Hz",
        change_requires_stop=True,
    ),
    432: _advanced_program_parameter(
        number=432,
        name="Jog Accel/Decel",
        description=(
            "Sets the acceleration and deceleration time used in jog mode."
        ),
        engineering_unit="s",
        minimum="0.01",
        maximum="600.00",
        default="10.00",
        resolution="0.01 s",
        change_requires_stop=True,
    ),
    434: _advanced_program_parameter(
        number=434,
        name="DC Brake Time",
        description=(
            "Sets how long DC braking current is injected into the motor for "
            "applicable stop modes."
        ),
        engineering_unit="s",
        minimum="0.0",
        maximum="99.9",
        default="0.0",
        resolution="0.1 s",
        change_requires_stop=True,
    ),
    435: _advanced_program_parameter(
        number=435,
        name="DC Brake Level",
        description=(
            "Sets the maximum DC braking current applied to the motor for "
            "applicable stop modes."
        ),
        engineering_unit="A",
        minimum="0.00",
        maximum="Drive Rated Amps × 1.80",
        default="Drive Rated Amps × 0.05",
        resolution="0.01 A",
        change_requires_stop=True,
    ),
    439: _advanced_program_parameter(
        number=439,
        name="S Curve %",
        description=(
            "Sets the fixed S-curve shaping applied to acceleration and "
            "deceleration ramps, including jog."
        ),
        engineering_unit="%",
        minimum="0",
        maximum="100",
        default="0",
        resolution="1%",
        change_requires_stop=True,
    ),
    440: _advanced_program_parameter(
        number=440,
        name="PWM Frequency",
        description="Sets the carrier frequency for the PWM output waveform.",
        engineering_unit="kHz",
        minimum="2.0",
        maximum="16.0",
        default="4.0",
        resolution="0.1 kHz",
        change_requires_stop=False,
    ),
    441: _advanced_program_parameter(
        number=441,
        name="Droop Hertz@ FLA",
        description=(
            "Sets frequency droop at full-load current for applications such "
            "as load sharing."
        ),
        engineering_unit="Hz",
        minimum="0.0",
        maximum="10.0",
        default="0.0",
        resolution="0.1 Hz",
        change_requires_stop=True,
    ),
    486: _advanced_program_parameter(
        number=486,
        name="Shear Pin1 Level",
        description=(
            "Sets the current threshold above which a shear-pin fault occurs "
            "after the A487 delay; zero disables the function."
        ),
        engineering_unit="A",
        minimum="0.0",
        maximum="Drive Rated Amps × 2",
        default="0.0",
        resolution="0.1 A",
        change_requires_stop=True,
    ),
    487: _advanced_program_parameter(
        number=487,
        name="Shear Pin 1 Time",
        description=(
            "Sets how long current must remain at or above A486 before a "
            "shear-pin fault occurs."
        ),
        engineering_unit="s",
        minimum="0.00",
        maximum="30.00",
        default="0.00",
        resolution="0.01 s",
        change_requires_stop=True,
    ),
    490: _advanced_program_parameter(
        number=490,
        name="Load Loss Level",
        description=(
            "Sets the current threshold below which a load-loss fault occurs "
            "after the A491 delay."
        ),
        engineering_unit="A",
        minimum="0.0",
        maximum="Drive Rated Amps",
        default="0.0",
        resolution="0.1 A",
        change_requires_stop=True,
    ),
    491: _advanced_program_parameter(
        number=491,
        name="Load Loss Time",
        description=(
            "Sets how long current must remain below A490 before a load-loss "
            "fault occurs."
        ),
        engineering_unit="s",
        minimum="0",
        maximum="9999",
        default="0",
        resolution="1 s",
        change_requires_stop=True,
    ),
    534: _advanced_program_parameter(
        number=534,
        name="Maximum Voltage",
        description="Sets the highest voltage that the drive outputs.",
        engineering_unit="V AC",
        minimum=(
            "10 (230 V drive), 20 (460 V drive), or 25 (600 V drive)"
        ),
        maximum=(
            "255 (230 V drive), 510 (460 V drive), or 637.5 (600 V drive)"
        ),
        default="Drive Rated Volts",
        resolution="1 V AC",
        change_requires_stop=True,
    ),
    535: _advanced_program_parameter(
        number=535,
        name="Motor Fdbk Type",
        description=(
            "Selects the motor speed-feedback device and its signal-checking "
            "mode."
        ),
        default="0",
        options=_MOTOR_FEEDBACK_OPTIONS,
        option_set_name="Motor Feedback Type",
        change_requires_stop=True,
    ),
    536: _advanced_program_parameter(
        number=536,
        name="Encoder PPR",
        description=(
            "Sets the encoder pulses per revolution when an encoder feedback "
            "device is used."
        ),
        engineering_unit="PPR",
        minimum="1",
        maximum="20000",
        default="1024",
        resolution="1 PPR",
        change_requires_stop=False,
    ),
    537: _advanced_program_parameter(
        number=537,
        name="Pulse In Scale",
        description=(
            "Sets the gain used to convert pulse-input frequency to output "
            "frequency."
        ),
        minimum="0",
        maximum="20000",
        default="64",
        resolution="1",
        change_requires_stop=False,
    ),
    543: _advanced_program_parameter(
        number=543,
        name="Start At PowerUp",
        description=(
            "Selects whether a maintained run signal may start the drive "
            "after power-up without being cycled."
        ),
        default="0",
        options=_DISABLED_ENABLED_OPTIONS,
        option_set_name="Disabled / Enabled",
        change_requires_stop=True,
    ),
    544: _advanced_program_parameter(
        number=544,
        name="Reverse Disable",
        description=(
            "Selects whether commands may change the direction of motor "
            "rotation."
        ),
        default="0",
        options=_REVERSE_DISABLE_OPTIONS,
        option_set_name="Reverse Direction Permission",
        change_requires_stop=True,
    ),
    545: _advanced_program_parameter(
        number=545,
        name="Flying Start En",
        description=(
            "Selects whether the drive catches a spinning motor and ramps "
            "from its detected speed at each start."
        ),
        default="0",
        options=_DISABLED_ENABLED_OPTIONS,
        option_set_name="Disabled / Enabled",
        change_requires_stop=False,
    ),
    546: _advanced_program_parameter(
        number=546,
        name="FlyStrt CurLimit",
        description=(
            "Sets the current threshold used to determine when flying start "
            "has matched motor frequency."
        ),
        engineering_unit="%",
        minimum="30",
        maximum="200",
        default="65",
        resolution="1%",
        change_requires_stop=False,
    ),
    547: _advanced_program_parameter(
        number=547,
        name="Compensation",
        description=(
            "Selects electrical or mechanical correction intended to improve "
            "motor stability."
        ),
        default="1",
        options=_COMPENSATION_OPTIONS,
        option_set_name="Motor Stability Compensation",
        change_requires_stop=False,
    ),
    548: _advanced_program_parameter(
        number=548,
        name="Power Loss Mode",
        description="Selects the drive response to loss of input power.",
        default="0",
        options=_POWER_LOSS_OPTIONS,
        option_set_name="Power Loss Response",
        change_requires_stop=False,
    ),
    550: _advanced_program_parameter(
        number=550,
        name="Bus Reg Enable",
        description="Selects whether DC-bus regulation is enabled.",
        default="1",
        options=_DISABLED_ENABLED_OPTIONS,
        option_set_name="Disabled / Enabled",
        change_requires_stop=False,
    ),
    551: _advanced_program_parameter(
        number=551,
        name="Fault Clear",
        description=(
            "Issues a command to reset the active fault or clear the fault "
            "history buffer."
        ),
        default="0",
        options=_FAULT_CLEAR_OPTIONS,
        option_set_name="Fault Clear Command",
        change_requires_stop=True,
    ),
    555: _advanced_program_parameter(
        number=555,
        name="Reset Meters",
        description=(
            "Issues a command to reset accumulated energy values or elapsed "
            "time values."
        ),
        default="0",
        options=_RESET_METERS_OPTIONS,
        option_set_name="Meter Reset Command",
        change_requires_stop=False,
    ),
    559: _advanced_program_parameter(
        number=559,
        name="Counts Per Unit",
        description=(
            "Sets the number of encoder counts represented by one "
            "application-defined position unit."
        ),
        minimum="1",
        maximum="32000",
        default="4096",
        resolution="1",
        change_requires_stop=False,
    ),
    572: _advanced_program_parameter(
        number=572,
        name="Speed Ratio",
        description="Sets the scale factor applied to the drive speed command.",
        minimum="0.01",
        maximum="99.99",
        default="1.00",
        resolution="0.01",
        change_requires_stop=True,
    ),
    575: _advanced_program_parameter(
        number=575,
        name="Flux Braking En",
        description="Selects whether flux braking is enabled.",
        default="0",
        options=_DISABLED_ENABLED_OPTIONS,
        option_set_name="Disabled / Enabled",
        change_requires_stop=False,
    ),
    576: _advanced_program_parameter(
        number=576,
        name="Phase Loss Level",
        description=(
            "Sets the per-phase current threshold used to detect output phase "
            "loss; a lower value reduces sensitivity."
        ),
        engineering_unit="%",
        minimum="0.0",
        maximum="100.0",
        default="25.0 (induction motor) or 4.0 (PM motor)",
        resolution="0.1%",
        change_requires_stop=False,
    ),
    604: _historical_fault_code_parameter(604, 4),
    605: _historical_fault_code_parameter(605, 5),
    606: _historical_fault_code_parameter(606, 6),
    607: _historical_fault_code_parameter(607, 7),
    608: _historical_fault_code_parameter(608, 8),
    609: _historical_fault_code_parameter(609, 9),
    610: _historical_fault_code_parameter(610, 10),
    631: _historical_fault_frequency_parameter(631, 1),
    632: _historical_fault_frequency_parameter(632, 2),
    633: _historical_fault_frequency_parameter(633, 3),
    634: _historical_fault_frequency_parameter(634, 4),
    635: _historical_fault_frequency_parameter(635, 5),
    636: _historical_fault_frequency_parameter(636, 6),
    637: _historical_fault_frequency_parameter(637, 7),
    638: _historical_fault_frequency_parameter(638, 8),
    639: _historical_fault_frequency_parameter(639, 9),
    640: _historical_fault_frequency_parameter(640, 10),
    641: _historical_fault_current_parameter(641, 1),
    642: _historical_fault_current_parameter(642, 2),
    643: _historical_fault_current_parameter(643, 3),
    644: _historical_fault_current_parameter(644, 4),
    645: _historical_fault_current_parameter(645, 5),
    646: _historical_fault_current_parameter(646, 6),
    647: _historical_fault_current_parameter(647, 7),
    648: _historical_fault_current_parameter(648, 8),
    649: _historical_fault_current_parameter(649, 9),
    650: _historical_fault_current_parameter(650, 10),
    651: _historical_fault_bus_voltage_parameter(651, 1),
    652: _historical_fault_bus_voltage_parameter(652, 2),
    653: _historical_fault_bus_voltage_parameter(653, 3),
    654: _historical_fault_bus_voltage_parameter(654, 4),
    655: _historical_fault_bus_voltage_parameter(655, 5),
    656: _historical_fault_bus_voltage_parameter(656, 6),
    657: _historical_fault_bus_voltage_parameter(657, 7),
    658: _historical_fault_bus_voltage_parameter(658, 8),
    659: _historical_fault_bus_voltage_parameter(659, 9),
    660: _historical_fault_bus_voltage_parameter(660, 10),
    693: _active_network_octet_parameter(
        number=693,
        address_kind="IP Address",
        octet=1,
    ),
    694: _active_network_octet_parameter(
        number=694,
        address_kind="IP Address",
        octet=2,
    ),
    695: _active_network_octet_parameter(
        number=695,
        address_kind="IP Address",
        octet=3,
    ),
    696: _active_network_octet_parameter(
        number=696,
        address_kind="IP Address",
        octet=4,
    ),
    697: _active_network_octet_parameter(
        number=697,
        address_kind="Subnet Mask",
        octet=1,
    ),
    698: _active_network_octet_parameter(
        number=698,
        address_kind="Subnet Mask",
        octet=2,
    ),
    699: _active_network_octet_parameter(
        number=699,
        address_kind="Subnet Mask",
        octet=3,
    ),
    700: _active_network_octet_parameter(
        number=700,
        address_kind="Subnet Mask",
        octet=4,
    ),
    701: _active_network_octet_parameter(
        number=701,
        address_kind="Gateway Address",
        octet=1,
    ),
    702: _active_network_octet_parameter(
        number=702,
        address_kind="Gateway Address",
        octet=2,
    ),
    703: _active_network_octet_parameter(
        number=703,
        address_kind="Gateway Address",
        octet=3,
    ),
    704: _active_network_octet_parameter(
        number=704,
        address_kind="Gateway Address",
        octet=4,
    ),
}
