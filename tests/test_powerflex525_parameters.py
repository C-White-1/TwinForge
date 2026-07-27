import pytest

from twinforge.knowledge.powerflex525_parameters import (
    POWERFLEX_525_PARAMETER_REFERENCE,
    PowerFlex525ParameterCatalogue,
)


def test_catalogue_covers_exactly_the_163_observed_aoi_parameters():
    expected = {
        *range(1, 10),
        *range(12, 18),
        *range(19, 23),
        *range(27, 30),
        *range(31, 52),
        53,
        *range(62, 71),
        *range(72, 74),
        *range(75, 78),
        *range(79, 83),
        *range(84, 86),
        88,
        90,
        99,
        *range(105, 107),
        *range(143, 145),
        *range(360, 365),
        367,
        369,
        *range(375, 377),
        378,
        *range(380, 383),
        *range(393, 395),
        *range(431, 433),
        *range(434, 436),
        *range(439, 442),
        *range(486, 488),
        *range(490, 492),
        *range(534, 538),
        *range(543, 549),
        *range(550, 552),
        555,
        559,
        572,
        *range(575, 577),
        *range(604, 611),
        *range(631, 661),
        *range(693, 705),
    }

    numbers = PowerFlex525ParameterCatalogue().curated_numbers()

    assert len(numbers) == 163
    assert set(numbers) == expected


def test_maps_qa_advisories_to_affected_parameters():
    catalogue = PowerFlex525ParameterCatalogue()

    assert [item.code for item in catalogue.advisories(105)] == [
        "PF525-QA-001",
        "PF525-QA-002",
        "PF525-QA-005",
    ]
    assert catalogue.advisories(544)[0].severity.value == "High"
    assert catalogue.advisories(1) == ()


def test_resolves_curated_parameter_definition():
    catalogue = PowerFlex525ParameterCatalogue()

    definition = catalogue.definition(34)

    assert definition is not None
    assert definition.code == "P034"
    assert definition.name == "Motor NP FLA"
    assert definition.engineering_unit == "A"
    assert definition.maximum == "Drive Rated Amps × 2"
    assert definition.minimum == "0.1"
    assert definition.default == "Based on Drive Rating"
    assert definition.reference == POWERFLEX_525_PARAMETER_REFERENCE


def test_preserves_enumerated_options_and_unknown_parameters():
    catalogue = PowerFlex525ParameterCatalogue()

    definition = catalogue.definition(38)

    assert definition is not None
    assert [(option.value, option.label) for option in definition.options] == [
        ("2", "Low Voltage (480 V)"),
        ("3", "High Voltage (600 V)"),
    ]
    assert definition.change_requires_stop
    assert catalogue.definition(999) is None


@pytest.mark.parametrize(
    ("number", "code"),
    [
        (31, "P031"),
        (32, "P032"),
        (33, "P033"),
        (34, "P034"),
        (35, "P035"),
        (36, "P036"),
        (37, "P037"),
        (38, "P038"),
        (39, "P039"),
        (40, "P040"),
        (41, "P041"),
        (42, "P042"),
        (43, "P043"),
        (44, "P044"),
        (45, "P045"),
        (46, "P046"),
        (47, "P047"),
        (48, "P048"),
        (49, "P049"),
        (50, "P050"),
        (51, "P051"),
        (53, "P053"),
    ],
)
def test_covers_every_observed_basic_program_parameter(
    number: int,
    code: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == code
    assert definition.group_name == "Basic Program"


def test_distinguishes_stop_required_parameters():
    catalogue = PowerFlex525ParameterCatalogue()
    minimum_frequency = catalogue.definition(43)
    maximum_frequency = catalogue.definition(44)
    stop_mode = catalogue.definition(45)

    assert minimum_frequency is not None
    assert minimum_frequency.change_requires_stop
    assert maximum_frequency is not None
    assert maximum_frequency.change_requires_stop
    assert stop_mode is not None
    assert not stop_mode.change_requires_stop


@pytest.mark.parametrize(
    ("number", "name"),
    [
        (143, "EN Comm Flt Actn"),
        (144, "EN Idle Flt Actn"),
    ],
)
def test_covers_observed_communications_parameters(
    number: int,
    name: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.group_prefix == "C"
    assert definition.group_name == "Communications"
    assert definition.default == "0"
    assert [(option.value, option.label) for option in definition.options] == [
        ("0", "Fault"),
        ("1", "Stop"),
        ("2", "Zero Data"),
        ("3", "Hold Last"),
        ("4", "Send Fault Configuration"),
    ]
    assert "commissioning verification" in (definition.description or "")


@pytest.mark.parametrize(
    ("number", "name", "default"),
    [
        (62, "DigIn TermBlk 02", "48"),
        (63, "DigIn TermBlk 03", "50"),
        (65, "DigIn TermBlk 05", "7"),
        (66, "DigIn TermBlk 06", "7"),
        (67, "DigIn TermBlk 07", "5"),
        (68, "DigIn TermBlk 08", "9"),
    ],
)
def test_covers_programmable_digital_inputs(
    number: int,
    name: str,
    default: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.default == default
    assert definition.group_name == "Terminal Block"
    assert definition.change_requires_stop
    assert len(definition.options) == 53
    assert definition.options[0].label == "Not Used"
    assert definition.options[-1].label == "Pulse Train"
    assert definition.option_set_name == "Programmable Digital Input"


def test_covers_two_wire_trigger_mode_separately():
    definition = PowerFlex525ParameterCatalogue().definition(64)

    assert definition is not None
    assert definition.name == "2-Wire Mode"
    assert definition.default == "0"
    assert [option.label for option in definition.options] == [
        "Edge Trigger",
        "Level Sense",
        "High-Speed Edge",
        "Momentary",
    ]
    assert "restart" in (definition.description or "")


@pytest.mark.parametrize(
    ("number", "name", "default"),
    [
        (69, "Opto Out1 Sel", "2"),
        (72, "Opto Out2 Sel", "1"),
    ],
)
def test_covers_programmable_opto_output_selection(
    number: int,
    name: str,
    default: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.default == default
    assert definition.option_set_name == "Programmable Digital Output"
    assert len(definition.options) == 32
    assert definition.options[0].label == "Ready/Fault"
    assert definition.options[-1].label == "Auto-Restart Countdown"


@pytest.mark.parametrize(
    ("number", "name", "selector"),
    [
        (70, "Opto Out1 Level", "T069"),
        (73, "Opto Out2 Level", "T072"),
    ],
)
def test_preserves_dependent_opto_output_level_semantics(
    number: int,
    name: str,
    selector: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.minimum == "0.0"
    assert definition.maximum == "9999.0"
    assert definition.engineering_unit is None
    assert selector in (definition.description or "")
    assert "units and valid range depend" in (definition.description or "")


def test_covers_opto_output_logic():
    definition = PowerFlex525ParameterCatalogue().definition(75)

    assert definition is not None
    assert definition.name == "Opto Out Logic"
    assert definition.default == "0"
    assert [option.label for option in definition.options] == [
        "Output 1 NO; Output 2 NO",
        "Output 1 NC; Output 2 NO",
        "Output 1 NO; Output 2 NC",
        "Output 1 NC; Output 2 NC",
    ]


@pytest.mark.parametrize(
    ("number", "name", "default"),
    [
        (76, "Relay Out1 Sel", "0"),
        (81, "Relay Out2 Sel", "2"),
    ],
)
def test_covers_programmable_relay_output_selection(
    number: int,
    name: str,
    default: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.default == default
    assert definition.option_set_name == "Programmable Digital Output"
    assert len(definition.options) == 32


@pytest.mark.parametrize(
    ("number", "name", "selector"),
    [
        (77, "Relay Out1 Level", "T076"),
        (82, "Relay Out2 Level", "T081"),
    ],
)
def test_preserves_dependent_relay_output_level_semantics(
    number: int,
    name: str,
    selector: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.minimum == "0.0"
    assert definition.maximum == "9999.0"
    assert definition.engineering_unit is None
    assert selector in (definition.description or "")


@pytest.mark.parametrize(
    ("number", "name"),
    [
        (79, "Relay 1 On Time"),
        (80, "Relay 1 Off Time"),
        (84, "Relay 2 On Time"),
        (85, "Relay 2 Off Time"),
    ],
)
def test_covers_relay_output_delays(number: int, name: str):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == "s"
    assert definition.minimum == "0.0"
    assert definition.maximum == "600.0"
    assert definition.default == "0.0"
    assert definition.resolution == "0.1 s"


def test_covers_analog_output_selection_and_setpoint_dependency():
    catalogue = PowerFlex525ParameterCatalogue()
    selection = catalogue.definition(88)
    setpoint = catalogue.definition(90)

    assert selection is not None
    assert selection.name == "Analog Out Sel"
    assert selection.option_set_name == "Analog Output Selection"
    assert len(selection.options) == 24
    assert selection.options[6].label == "Setpoint 0–10 V"
    assert selection.options[14].label == "Setpoint 0–20 mA"
    assert selection.options[22].label == "Setpoint 4–20 mA"
    assert setpoint is not None
    assert setpoint.engineering_unit == "%"
    assert setpoint.minimum == "0.0"
    assert setpoint.maximum == "100.0"
    assert "6, 14, or 22" in (setpoint.description or "")


def test_covers_analog_input_filter():
    definition = PowerFlex525ParameterCatalogue().definition(99)

    assert definition is not None
    assert definition.name == "Analog In Filter"
    assert definition.minimum == "0"
    assert definition.maximum == "14"
    assert definition.default == "0"
    assert "doubles" in (definition.description or "")


@pytest.mark.parametrize(
    ("number", "name", "labels"),
    [
        (
            105,
            "Safety Open Enable",
            ["Fault Enable", "Fault Disable"],
        ),
        (
            106,
            "Safety Fault Reset Configuration",
            ["Power-Cycle Reset", "Fault-Clear Reset"],
        ),
    ],
)
def test_covers_safety_input_configuration(
    number: int,
    name: str,
    labels: list[str],
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.default == "0"
    assert [option.label for option in definition.options] == labels
    assert definition.group_name == "Terminal Block"


@pytest.mark.parametrize(
    ("number", "name", "unit"),
    [
        (1, "Output Freq", "Hz"),
        (2, "Commanded Freq", "Hz"),
        (3, "Output Current", "A"),
        (4, "Output Voltage", "V"),
        (5, "DC Bus Voltage", "V DC"),
    ],
)
def test_covers_basic_drive_measurements(
    number: int,
    name: str,
    unit: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == unit
    assert definition.read_only
    assert definition.group_name == "Basic Display"


def test_preserves_drive_status_flags():
    definition = PowerFlex525ParameterCatalogue().definition(6)

    assert definition is not None
    assert definition.read_only
    assert [(flag.position, flag.label) for flag in definition.flags] == [
        ("Digit 1", "Running"),
        ("Digit 2", "Forward"),
        ("Digit 3", "Accelerating"),
        ("Digit 4", "Decelerating"),
        ("Digit 5", "Safety Active"),
    ]


@pytest.mark.parametrize(
    ("number", "name"),
    [
        (7, "Fault 1 Code"),
        (8, "Fault 2 Code"),
        (9, "Fault 3 Code"),
    ],
)
def test_covers_recent_fault_history(number: int, name: str):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.minimum == "F0"
    assert definition.maximum == "F127"
    assert definition.read_only


def test_preserves_encoded_control_source_fields():
    definition = PowerFlex525ParameterCatalogue().definition(12)

    assert definition is not None
    assert definition.read_only
    assert [(field.position, field.label) for field in definition.fields] == [
        ("Digit 1", "Start command source"),
        ("Digits 2–3", "Frequency command source"),
        ("Digit 4", "Frequency override"),
    ]
    assert definition.fields[0].options[-1].label == "EtherNet/IP"
    assert definition.fields[1].options[0].label == "Other"
    assert definition.fields[1].options[-1].value == "16"
    assert definition.fields[2].options[-1].label == "Purge"


@pytest.mark.parametrize(
    ("number", "labels"),
    [
        (
            13,
            [
                "Terminal 1 Closed",
                "Terminal 2 Closed",
                "Terminal 3 Closed",
                "Dynamic-Brake Transistor On",
            ],
        ),
        (
            14,
            [
                "Terminal 5 Closed",
                "Terminal 6 Closed",
                "Terminal 7 Closed",
                "Terminal 8 Closed",
            ],
        ),
    ],
)
def test_preserves_control_input_status_flags(
    number: int,
    labels: list[str],
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.read_only
    assert [flag.label for flag in definition.flags] == labels


@pytest.mark.parametrize(
    ("number", "name", "unit"),
    [
        (15, "Output RPM", "rpm"),
        (16, "Output Speed", "%"),
        (17, "Output Power", "kW"),
    ],
)
def test_covers_output_speed_and_power(
    number: int,
    name: str,
    unit: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == unit
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "name", "unit", "resolution"),
    [
        (19, "Elapsed Run Time", "h", "10 h"),
        (20, "Average Power", "kW", "0.01 kW"),
        (21, "Elapsed kWh", "kWh", "0.1 kWh"),
        (22, "Elapsed MWh", "MWh", "0.1 MWh"),
        (27, "Drive Temp", "°C", "1 °C"),
        (28, "Control Temp", "°C", "1 °C"),
    ],
)
def test_covers_runtime_energy_and_temperature(
    number: int,
    name: str,
    unit: str,
    resolution: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == unit
    assert definition.resolution == resolution
    assert definition.read_only


def test_covers_control_software_version():
    definition = PowerFlex525ParameterCatalogue().definition(29)

    assert definition is not None
    assert definition.name == "Control SW Version"
    assert definition.minimum == "0.000"
    assert definition.maximum == "65.535"
    assert definition.resolution == "0.001"
    assert definition.engineering_unit is None
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "name", "unit", "maximum", "resolution"),
    [
        (360, "Analog In 0-10V", "%", "100.0", "0.1%"),
        (361, "Analog In 4-20mA", "%", "100.0", "0.1%"),
        (362, "Elapsed Time-hr", "h", "32767", "1 h"),
        (363, "Elapsed Time-min", "min", "60.0", "0.1 min"),
        (364, "Counter Status", None, "65535", "1"),
        (367, "Drive Type", None, "65535", "1"),
    ],
)
def test_covers_advanced_display_inputs_time_and_status(
    number: int,
    name: str,
    unit: str | None,
    maximum: str,
    resolution: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"d{number:03d}"
    assert definition.name == name
    assert definition.group_name == "Advanced Display"
    assert definition.engineering_unit == unit
    assert definition.maximum == maximum
    assert definition.resolution == resolution
    assert definition.read_only


def test_distinguishes_powered_up_time_from_outputting_power_time():
    catalogue = PowerFlex525ParameterCatalogue()

    powered_up_hours = catalogue.definition(362)
    outputting_power_hours = catalogue.definition(19)

    assert powered_up_hours is not None
    assert outputting_power_hours is not None
    assert "powered-up" in (powered_up_hours.description or "")
    assert powered_up_hours.resolution == "1 h"
    assert "outputting power" in (outputting_power_hours.description or "")
    assert outputting_power_hours.resolution == "10 h"


@pytest.mark.parametrize(
    ("number", "name", "unit", "resolution"),
    [
        (369, "Motor OL Level", "%", "0.1%"),
        (375, "Slip Hz Meter", "Hz", "0.1 Hz"),
        (376, "Speed Feedback", "rpm", "0.1 rpm"),
        (378, "Encoder Speed", "rpm", "0.1 rpm"),
        (380, "DC Bus Ripple", "V DC", "1 V DC"),
        (381, "Output Powr Fctr", "°", "0.1°"),
        (382, "Torque Current", "A", "0.01 A"),
    ],
)
def test_covers_advanced_display_measurements(
    number: int,
    name: str,
    unit: str,
    resolution: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == unit
    assert definition.resolution == resolution
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "expected_flags"),
    [
        (
            393,
            {
                "0": "Jogging",
                "8": "Current Limiting",
                "10": "Safety Input 1",
                "13": "Safe Torque Permit",
            },
        ),
        (
            394,
            {
                "0": "Relay Output 1",
                "1": "Relay Output 2",
                "2": "Opto Output 1",
                "3": "Opto Output 2",
            },
        ),
    ],
)
def test_preserves_advanced_display_status_bits(
    number: int,
    expected_flags: dict[str, str],
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    actual_flags = {flag.position: flag.label for flag in definition.flags}
    assert actual_flags.items() >= expected_flags.items()
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "name", "unit", "default", "requires_stop"),
    [
        (431, "Jog Frequency", "Hz", "10.00", True),
        (432, "Jog Accel/Decel", "s", "10.00", True),
        (434, "DC Brake Time", "s", "0.0", True),
        (435, "DC Brake Level", "A", "Drive Rated Amps × 0.05", True),
        (439, "S Curve %", "%", "0", True),
        (440, "PWM Frequency", "kHz", "4.0", False),
        (441, "Droop Hertz@ FLA", "Hz", "0.0", True),
    ],
)
def test_covers_advanced_program_motion_and_braking(
    number: int,
    name: str,
    unit: str,
    default: str,
    requires_stop: bool,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"A{number:03d}"
    assert definition.name == name
    assert definition.group_name == "Advanced Program"
    assert definition.engineering_unit == unit
    assert definition.default == default
    assert definition.change_requires_stop is requires_stop
    assert not definition.read_only


@pytest.mark.parametrize(
    ("number", "name", "unit", "maximum", "resolution"),
    [
        (486, "Shear Pin1 Level", "A", "Drive Rated Amps × 2", "0.1 A"),
        (487, "Shear Pin 1 Time", "s", "30.00", "0.01 s"),
        (490, "Load Loss Level", "A", "Drive Rated Amps", "0.1 A"),
        (491, "Load Loss Time", "s", "9999", "1 s"),
    ],
)
def test_covers_advanced_program_protection_thresholds(
    number: int,
    name: str,
    unit: str,
    maximum: str,
    resolution: str,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == unit
    assert definition.maximum == maximum
    assert definition.resolution == resolution
    assert definition.default in {"0", "0.0", "0.00"}
    assert definition.change_requires_stop


@pytest.mark.parametrize(
    ("number", "name", "unit", "default", "requires_stop"),
    [
        (534, "Maximum Voltage", "V AC", "Drive Rated Volts", True),
        (536, "Encoder PPR", "PPR", "1024", False),
        (537, "Pulse In Scale", None, "64", False),
    ],
)
def test_covers_advanced_program_feedback_scaling(
    number: int,
    name: str,
    unit: str | None,
    default: str,
    requires_stop: bool,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.engineering_unit == unit
    assert definition.default == default
    assert definition.change_requires_stop is requires_stop


def test_preserves_motor_feedback_type_options():
    definition = PowerFlex525ParameterCatalogue().definition(535)

    assert definition is not None
    assert definition.option_set_name == "Motor Feedback Type"
    assert [(option.value, option.label) for option in definition.options] == [
        ("0", "None"),
        ("1", "Pulse Train"),
        ("2", "Single Channel"),
        ("3", "Single Channel with Check"),
        ("4", "Quadrature"),
        ("5", "Quadrature with Check"),
    ]
    assert definition.change_requires_stop


@pytest.mark.parametrize(
    ("number", "name", "default", "requires_stop"),
    [
        (543, "Start At PowerUp", "0", True),
        (544, "Reverse Disable", "0", True),
        (545, "Flying Start En", "0", False),
        (547, "Compensation", "1", False),
        (548, "Power Loss Mode", "0", False),
        (550, "Bus Reg Enable", "1", False),
    ],
)
def test_covers_advanced_program_start_and_power_behaviour(
    number: int,
    name: str,
    default: str,
    requires_stop: bool,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.default == default
    assert definition.options
    assert definition.change_requires_stop is requires_stop


def test_uses_manual_flying_start_current_limit_default():
    definition = PowerFlex525ParameterCatalogue().definition(546)

    assert definition is not None
    assert definition.engineering_unit == "%"
    assert definition.minimum == "30"
    assert definition.maximum == "200"
    assert definition.default == "65"
    assert definition.resolution == "1%"


@pytest.mark.parametrize(
    ("number", "name", "default", "requires_stop"),
    [
        (551, "Fault Clear", "0", True),
        (555, "Reset Meters", "0", False),
        (559, "Counts Per Unit", "4096", False),
        (572, "Speed Ratio", "1.00", True),
        (575, "Flux Braking En", "0", False),
        (
            576,
            "Phase Loss Level",
            "25.0 (induction motor) or 4.0 (PM motor)",
            False,
        ),
    ],
)
def test_covers_remaining_advanced_program_parameters(
    number: int,
    name: str,
    default: str,
    requires_stop: bool,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.name == name
    assert definition.default == default
    assert definition.change_requires_stop is requires_stop


@pytest.mark.parametrize(
    ("number", "option_set_name", "values"),
    [
        (551, "Fault Clear Command", ["0", "1", "2"]),
        (555, "Meter Reset Command", ["0", "1", "2"]),
        (575, "Disabled / Enabled", ["0", "1"]),
    ],
)
def test_preserves_remaining_advanced_program_options(
    number: int,
    option_set_name: str,
    values: list[str],
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.option_set_name == option_set_name
    assert [option.value for option in definition.options] == values


@pytest.mark.parametrize(
    ("number", "history_position"),
    [
        (604, 4),
        (605, 5),
        (606, 6),
        (607, 7),
        (608, 8),
        (609, 9),
        (610, 10),
    ],
)
def test_covers_extended_fault_code_history(
    number: int,
    history_position: int,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"F{number:03d}"
    assert definition.name == f"Fault {history_position} Code"
    assert definition.group_name == "Fault and Diagnostic"
    assert str(history_position) in (definition.description or "")
    assert definition.minimum == "F0"
    assert definition.maximum == "F127"
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "history_position"),
    [(number, number - 630) for number in range(631, 641)],
)
def test_covers_fault_history_frequency_snapshots(
    number: int,
    history_position: int,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"F{number}"
    assert definition.name == f"Fault {history_position} Frequency"
    assert definition.group_name == "Fault and Diagnostic"
    assert f"entry {history_position}" in (definition.description or "")
    assert definition.engineering_unit == "Hz"
    assert definition.minimum == "0.00"
    assert definition.maximum == "500.00"
    assert definition.resolution == "0.01 Hz"
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "history_position"),
    [(number, number - 640) for number in range(641, 651)],
)
def test_covers_fault_history_current_snapshots(
    number: int,
    history_position: int,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"F{number}"
    assert definition.name == f"Fault {history_position} Current"
    assert definition.group_name == "Fault and Diagnostic"
    assert f"entry {history_position}" in (definition.description or "")
    assert definition.engineering_unit == "A"
    assert definition.minimum == "0.00"
    assert definition.maximum == "Drive Rated Amps x 2"
    assert definition.resolution == "0.01 A"
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "history_position"),
    [(number, number - 650) for number in range(651, 661)],
)
def test_covers_fault_history_bus_voltage_snapshots(
    number: int,
    history_position: int,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"F{number}"
    assert definition.name == f"Fault {history_position} DC Bus Voltage"
    assert definition.group_name == "Fault and Diagnostic"
    assert f"entry {history_position}" in (definition.description or "")
    assert definition.engineering_unit == "V DC"
    assert definition.minimum == "0"
    assert definition.maximum == "1200"
    assert definition.resolution == "1 V DC"
    assert definition.read_only


@pytest.mark.parametrize(
    ("number", "address_kind", "octet"),
    [
        *[(number, "IP Address", number - 692) for number in range(693, 697)],
        *[(number, "Subnet Mask", number - 696) for number in range(697, 701)],
        *[
            (number, "Gateway Address", number - 700)
            for number in range(701, 705)
        ],
    ],
)
def test_covers_active_network_address_octets(
    number: int,
    address_kind: str,
    octet: int,
):
    definition = PowerFlex525ParameterCatalogue().definition(number)

    assert definition is not None
    assert definition.code == f"F{number}"
    assert definition.name == f"Active {address_kind} Octet {octet}"
    assert definition.group_name == "Fault and Diagnostic"
    assert f"octet {octet}" in (definition.description or "")
    assert "currently used" in (definition.description or "")
    assert definition.minimum == "0"
    assert definition.maximum == "255"
    assert definition.resolution == "1"
    assert definition.read_only
