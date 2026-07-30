"""CODESYS project composition for the neutral PowerFlex 525 IEC core."""

from __future__ import annotations

from dataclasses import dataclass
import re

from twinforge.exporters.codesys_ir_integration import (
    CodesysArgumentBinding,
    CodesysProgramCall,
    CodesysProgramVariable,
    CodesysProjectIntegration,
    codesys_parameter_initial_value,
    codesys_program_variable_name,
)
from twinforge.exporters.codesys_sys_module_iec import (
    build_codesys_sys_module_binding_unit,
    codesys_sys_module_binding_integration,
)
from twinforge.exporters.powerflex525_core import (
    build_powerflex525_iec_unit,
)
from twinforge.ir import IRDirection


_IEC_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class PowerFlex525CodesysDevice:
    """Identify one physical drive and its native CODESYS device object."""

    name: str
    device_variable: str

    def __post_init__(self) -> None:
        """Reject names that cannot safely form IEC identifiers."""

        if _IEC_IDENTIFIER.fullmatch(self.name) is None:
            raise ValueError(
                "PowerFlex device name must be an IEC 61131-3 identifier"
            )
        if _IEC_IDENTIFIER.fullmatch(self.device_variable) is None:
            raise ValueError(
                "device_variable must be an IEC 61131-3 identifier"
            )


def powerflex525_codesys_integration() -> CodesysProjectIntegration:
    """Return a runnable CODESYS program/task wrapper for the neutral core."""

    unit = build_powerflex525_iec_unit()
    return CodesysProjectIntegration(
        instance_name="fbPowerFlex525",
        interval_ms=20,
        bindings=tuple(
            CodesysArgumentBinding(
                parameter.name,
                codesys_program_variable_name(parameter),
                initial_value=codesys_parameter_initial_value(parameter),
            )
            for parameter in unit.parameters
        ),
    )


def powerflex525_codesys_application_integration(
    device_variable: str,
) -> CodesysProjectIntegration:
    """Compose the portable core with CODESYS module diagnostics."""

    core = powerflex525_codesys_integration()
    module_unit = build_codesys_sys_module_binding_unit()
    module = codesys_sys_module_binding_integration(device_variable)
    parameters = {item.name: item for item in module_unit.parameters}
    module_variables = tuple(
        CodesysProgramVariable(
            binding.variable_name,
            parameters[binding.parameter_name].data_type or "BOOL",
            binding.dimensions,
            binding.initial_value,
        )
        for binding in module.bindings
    )
    arguments = []
    for binding in module.bindings:
        parameter = parameters[binding.parameter_name]
        operator = (
            "=>" if parameter.direction is IRDirection.OUTPUT else ":="
        )
        arguments.append(
            f"    {binding.parameter_name} {operator} "
            f"{binding.variable_name}"
        )
    module_call = (
        f"{module.instance_name}(\n" + ",\n".join(arguments) + "\n);"
    )
    return CodesysProjectIntegration(
        bindings=core.bindings,
        program_name=core.program_name,
        task_name=core.task_name,
        instance_name=core.instance_name,
        interval_ms=core.interval_ms,
        priority=core.priority,
        program_variables=(
            CodesysProgramVariable(module.instance_name, module_unit.name),
            *module_variables,
            *module.program_variables,
        ),
        statements_before_call=module.statements_before_call,
        statements_after_call=(
            module_call,
            *module.statements_after_call,
        ),
    )


def powerflex525_codesys_multi_application_integration(
    devices: tuple[PowerFlex525CodesysDevice, ...],
) -> CodesysProjectIntegration:
    """Compose isolated core and diagnostic calls for multiple drives."""

    if not devices:
        raise ValueError("at least one PowerFlex device is required")
    names = [item.name.casefold() for item in devices]
    if len(names) != len(set(names)):
        raise ValueError("PowerFlex device names must be unique")
    variables = [item.device_variable.casefold() for item in devices]
    if len(variables) != len(set(variables)):
        raise ValueError("CODESYS device variables must be unique")

    core_unit = build_powerflex525_iec_unit()
    module_unit = build_codesys_sys_module_binding_unit()
    calls: list[CodesysProgramCall] = []
    program_variables: list[CodesysProgramVariable] = []
    for device in devices:
        prefix = f"{device.name}_"
        module = codesys_sys_module_binding_integration(
            device.device_variable,
            symbol_prefix=prefix,
        )
        core_bindings = tuple(
            CodesysArgumentBinding(
                parameter.name,
                f"{prefix}{codesys_program_variable_name(parameter)}",
                initial_value=codesys_parameter_initial_value(parameter),
            )
            for parameter in core_unit.parameters
        )
        calls.append(
            CodesysProgramCall(
                core_unit.name,
                f"fbPowerFlex525_{device.name}",
                core_bindings,
                statements_before_call=module.statements_before_call,
            )
        )
        calls.append(
            CodesysProgramCall(
                module_unit.name,
                module.instance_name,
                module.bindings,
                statements_after_call=module.statements_after_call,
            )
        )
        program_variables.extend(module.program_variables)

    return CodesysProjectIntegration(
        bindings=(),
        interval_ms=20,
        program_variables=tuple(program_variables),
        calls=tuple(calls),
    )
