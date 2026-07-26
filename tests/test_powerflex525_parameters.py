import pytest

from twinforge.knowledge.powerflex525_parameters import (
    POWERFLEX_525_PARAMETER_REFERENCE,
    PowerFlex525ParameterCatalogue,
)


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
