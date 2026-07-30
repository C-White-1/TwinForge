from dataclasses import FrozenInstanceError

import pytest

from twinforge.exporters import (
    CodesysArgumentBinding,
    CodesysProjectIntegration,
)
from twinforge.exporters.codesys_ir_integration import (
    CodesysArgumentBinding as FocusedArgumentBinding,
    CodesysProjectIntegration as FocusedProjectIntegration,
    codesys_parameter_initial_value,
    codesys_program_variable_name,
)
from twinforge.exporters.codesys_plcopen_ir import (
    CodesysArgumentBinding as CompatibilityArgumentBinding,
)
from twinforge.ir import IRDirection, IRParameter


def _parameter(
    name: str,
    data_type: str | None,
    *,
    default_value: bool | int | float | str | None = None,
    default_lexical_value: str | None = None,
) -> IRParameter:
    return IRParameter(
        name=name,
        direction=IRDirection.INPUT,
        data_type=data_type,
        default_value=default_value,
        default_lexical_value=default_lexical_value,
    )


def test_public_and_compatibility_exports_reference_focused_types() -> None:
    assert CodesysArgumentBinding is FocusedArgumentBinding
    assert CompatibilityArgumentBinding is FocusedArgumentBinding
    assert CodesysProjectIntegration is FocusedProjectIntegration


@pytest.mark.parametrize(
    ("data_type", "expected"),
    [
        ("BOOL", "xCommand"),
        ("DINT", "diCommand"),
        ("LREAL", "lrCommand"),
        ("UDINT", "udiCommand"),
        ("CUSTOM", "vCommand"),
        (None, "vCommand"),
    ],
)
def test_program_variable_names_apply_type_prefix(
    data_type: str | None,
    expected: str,
) -> None:
    parameter = _parameter("Command", data_type)

    assert codesys_program_variable_name(parameter) == expected


def test_program_variable_name_sanitizes_source_identifier() -> None:
    parameter = _parameter(" Local:1:I.Data.0 ", "BOOL")

    assert codesys_program_variable_name(parameter) == "xLocal_1_I_Data_0"


def test_parameter_initial_value_preserves_lexical_evidence() -> None:
    assert (
        codesys_parameter_initial_value(
            _parameter(
                "Delay",
                "TIME",
                default_value=1000,
                default_lexical_value="T#1s",
            )
        )
        == "T#1s"
    )
    assert (
        codesys_parameter_initial_value(
            _parameter("Enabled", "BOOL", default_value=False)
        )
        == "FALSE"
    )
    assert (
        codesys_parameter_initial_value(_parameter("EnableIn", "BOOL"))
        == "TRUE"
    )


def test_integration_configuration_is_immutable_with_stable_defaults() -> None:
    integration = CodesysProjectIntegration(bindings=())

    assert integration.program_name == "PLC_PRG"
    assert integration.task_name == "MainTask"
    assert integration.interval_ms == 20
    assert integration.calls == ()
    with pytest.raises(FrozenInstanceError):
        integration.priority = 2  # type: ignore[misc]
