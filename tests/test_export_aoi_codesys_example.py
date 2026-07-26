from twinforge.exporters import (
    codesys_parameter_initial_value,
    codesys_program_variable_name,
)
from twinforge.ir import IRDirection, IRParameter


def test_program_binding_names_are_case_distinct_and_preserve_defaults():
    parameter = IRParameter(
        name="Inp_Interval",
        direction=IRDirection.INPUT,
        data_type="DINT",
        default_value=1000,
        default_lexical_value="1000",
    )

    assert codesys_program_variable_name(parameter) == "diInp_Interval"
    assert (
        codesys_program_variable_name(parameter).casefold()
        != parameter.name.casefold()
    )
    assert codesys_parameter_initial_value(parameter) == "1000"
