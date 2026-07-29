"""Neutral IEC unit construction for the verified PowerFlex 525 core."""

from __future__ import annotations

from twinforge.ir import (
    IRDirection,
    IRParameter,
    IRReusableUnit,
    IRRoutineRole,
    IRUnitKind,
    IRVariable,
    lower_structured_text,
)
from twinforge.structured_text import (
    CallKind,
    CallRule,
    SemanticContext,
    SemanticSymbol,
    SymbolKind,
    TypeConversionPolicy,
    analyze_semantics,
    parse_structured_text,
)

from .codesys_plcopen_ir import (
    CodesysArgumentBinding,
    CodesysProgramVariable,
    CodesysProjectIntegration,
    codesys_parameter_initial_value,
    codesys_program_variable_name,
)
from .codesys_sys_module_iec import (
    build_codesys_sys_module_binding_unit,
    codesys_sys_module_binding_integration,
)


_INPUTS = (
    ("Inp_Source", "DINT"),
    ("Inp_PRunFwd", "BOOL"),
    ("Inp_PRunRev", "BOOL"),
    ("Inp_PJogFwd", "BOOL"),
    ("Inp_PJogRev", "BOOL"),
    ("Inp_PStop", "BOOL"),
    ("Inp_PReset", "BOOL"),
    ("Inp_PSpeed", "REAL"),
    ("Inp_ORunFwd", "BOOL"),
    ("Inp_ORunRev", "BOOL"),
    ("Inp_OJogFwd", "BOOL"),
    ("Inp_OJogRev", "BOOL"),
    ("Inp_OStop", "BOOL"),
    ("Inp_OReset", "BOOL"),
    ("Inp_OSpeed", "REAL"),
    ("Inp_XRunFwd", "BOOL"),
    ("Inp_XRunRev", "BOOL"),
    ("Inp_XJogFwd", "BOOL"),
    ("Inp_XJogRev", "BOOL"),
    ("Inp_XStop", "BOOL"),
    ("Inp_XReset", "BOOL"),
    ("Inp_XSpeed", "REAL"),
    ("Inp_MRunFwd", "BOOL"),
    ("Inp_MRunRev", "BOOL"),
    ("Inp_MJogFwd", "BOOL"),
    ("Inp_MJogRev", "BOOL"),
    ("Inp_MStop", "BOOL"),
    ("Inp_MReset", "BOOL"),
    ("Inp_MSpeed", "REAL"),
    ("Inp_OvCmd", "DINT"),
    ("Inp_OvSpeed", "REAL"),
    ("Inp_PSetOverride", "BOOL"),
    ("Inp_MPSet", "REAL"),
    ("Inp_PermOK", "BOOL"),
    ("Inp_NBPermOK", "BOOL"),
    ("Inp_IntlkOK", "BOOL"),
    ("Inp_NBIntlkOK", "BOOL"),
    ("Inp_Bypass", "BOOL"),
    ("Inp_RunFwdAvail", "BOOL"),
    ("Inp_RunRevAvail", "BOOL"),
    ("Inp_JogFwdAvail", "BOOL"),
    ("Inp_JogRevAvail", "BOOL"),
    ("Inp_Ready", "BOOL"),
    ("Inp_Active", "BOOL"),
    ("Inp_ENetLogicCtrl", "BOOL"),
    ("Inp_KeypadCtrlSts", "BOOL"),
    ("Inp_KeypadCtrlCmd", "BOOL"),
    ("Inp_MaxSpeed", "REAL"),
    ("Inp_JogSpeed", "REAL"),
    ("Inp_StartDelayMs", "DINT"),
    ("Inp_ElapsedMs", "DINT"),
)
_OUTPUTS = (
    ("Out_LogicCommand", "UINT"),
    ("Out_SpeedCommand", "INT"),
    ("Out_RefSpeed", "REAL"),
    ("Out_PermOK", "BOOL"),
    ("Out_IntlkOK", "BOOL"),
    ("Out_RunFwd", "BOOL"),
    ("Out_RunRev", "BOOL"),
    ("Out_JogFwd", "BOOL"),
    ("Out_JogRev", "BOOL"),
    ("Out_Starting", "BOOL"),
    ("Out_Stopping", "BOOL"),
)
_LOCALS = (
    ("RunFwd", "BOOL"),
    ("RunRev", "BOOL"),
    ("StartElapsedMs", "DINT"),
    ("TimerDone", "BOOL"),
    ("StopCmd", "BOOL"),
    ("StartCmd", "BOOL"),
    ("JogCmd", "BOOL"),
    ("ResetCmd", "BOOL"),
    ("SpeedRef", "REAL"),
)

_BODY = """\
Out_PermOK := (Inp_PermOK OR Inp_Bypass) AND Inp_NBPermOK;
Out_IntlkOK := (Inp_IntlkOK OR Inp_Bypass) AND Inp_NBIntlkOK;

IF Inp_Source = 1 THEN
    IF Inp_PSetOverride THEN
        Out_RefSpeed := Inp_MPSet;
    ELSE
        Out_RefSpeed := Inp_PSpeed;
    END_IF;
    RunFwd := Inp_PRunFwd AND (Out_PermOK OR RunFwd)
        AND Out_IntlkOK AND NOT Inp_PStop;
    RunRev := Inp_PRunRev AND (Out_PermOK OR RunRev)
        AND Out_IntlkOK AND NOT Inp_PStop;
ELSIF Inp_Source = 2 THEN
    Out_RefSpeed := Inp_OSpeed;
    RunFwd := (RunFwd OR (Inp_ORunFwd AND Inp_RunFwdAvail
        AND Out_PermOK AND NOT Inp_ORunRev))
        AND Out_IntlkOK AND NOT Inp_OStop;
    RunRev := (RunRev OR (Inp_ORunRev AND Inp_RunRevAvail
        AND Out_PermOK AND NOT Inp_ORunFwd))
        AND Out_IntlkOK AND NOT Inp_OStop;
ELSIF Inp_Source = 3 THEN
    Out_RefSpeed := Inp_XSpeed;
    RunFwd := (RunFwd OR (Inp_XRunFwd AND Inp_RunFwdAvail
        AND Out_PermOK AND NOT Inp_XRunRev))
        AND Out_IntlkOK AND NOT Inp_XStop;
    RunRev := (RunRev OR (Inp_XRunRev AND Inp_RunRevAvail
        AND Out_PermOK AND NOT Inp_XRunFwd))
        AND Out_IntlkOK AND NOT Inp_XStop;
ELSIF Inp_Source = 4 THEN
    Out_RefSpeed := Inp_OvSpeed;
    IF (Inp_OvCmd = 1) OR NOT Out_IntlkOK THEN
        RunFwd := FALSE;
        RunRev := FALSE;
    ELSIF (Inp_OvCmd = 2) AND Out_PermOK THEN
        RunRev := FALSE;
        RunFwd := TRUE;
    ELSIF (Inp_OvCmd = 3) AND Out_PermOK THEN
        RunFwd := FALSE;
        RunRev := TRUE;
    END_IF;
ELSIF Inp_Source = 5 THEN
    Out_RefSpeed := Inp_MSpeed;
    RunFwd := (RunFwd OR (Inp_MRunFwd AND Inp_RunFwdAvail
        AND Out_PermOK AND NOT Inp_MRunRev))
        AND Out_IntlkOK AND NOT Inp_MStop;
    RunRev := (RunRev OR (Inp_MRunRev AND Inp_RunRevAvail
        AND Out_PermOK AND NOT Inp_MRunFwd))
        AND Out_IntlkOK AND NOT Inp_MStop;
ELSE
    Out_RefSpeed := 0.0;
    RunFwd := FALSE;
    RunRev := FALSE;
END_IF;

Out_JogFwd := (Inp_JogFwdAvail AND Out_PermOK AND
    (((Inp_Source = 2) AND Inp_OJogFwd AND NOT Inp_OJogRev)
    OR ((Inp_Source = 3) AND Inp_XJogFwd AND NOT Inp_XJogRev)
    OR ((Inp_Source = 5) AND Inp_MJogFwd AND NOT Inp_MJogRev)))
    OR ((Inp_Source = 1) AND Inp_PJogFwd AND NOT Inp_PJogRev);
Out_JogRev := (Inp_JogRevAvail AND Out_PermOK AND
    (((Inp_Source = 2) AND Inp_OJogRev AND NOT Inp_OJogFwd)
    OR ((Inp_Source = 3) AND Inp_XJogRev AND NOT Inp_XJogFwd)
    OR ((Inp_Source = 5) AND Inp_MJogRev AND NOT Inp_MJogFwd)))
    OR ((Inp_Source = 1) AND Inp_PJogRev AND NOT Inp_PJogFwd);

IF RunFwd OR RunRev THEN
    StartElapsedMs := StartElapsedMs + Inp_ElapsedMs;
    IF StartElapsedMs >= Inp_StartDelayMs THEN
        StartElapsedMs := Inp_StartDelayMs;
        TimerDone := TRUE;
    ELSE
        TimerDone := FALSE;
    END_IF;
ELSE
    StartElapsedMs := 0;
    TimerDone := FALSE;
END_IF;
Out_Starting := (RunFwd OR RunRev) AND NOT TimerDone;

StopCmd := Inp_Active AND Inp_ENetLogicCtrl
    AND NOT (Inp_KeypadCtrlSts OR RunFwd OR RunRev
    OR Out_JogFwd OR Out_JogRev);
StartCmd := Inp_Ready AND TimerDone AND NOT StopCmd
    AND (RunFwd OR RunRev OR Out_JogFwd OR Out_JogRev);
JogCmd := Inp_Ready AND NOT (StopCmd OR RunFwd OR RunRev)
    AND (Out_JogFwd OR Out_JogRev);
ResetCmd := Inp_PReset OR Inp_OReset OR Inp_XReset OR Inp_MReset;

Out_LogicCommand := 0;
IF StopCmd THEN Out_LogicCommand := Out_LogicCommand + 1; END_IF;
IF StartCmd THEN Out_LogicCommand := Out_LogicCommand + 2; END_IF;
IF JogCmd THEN Out_LogicCommand := Out_LogicCommand + 4; END_IF;
IF ResetCmd THEN Out_LogicCommand := Out_LogicCommand + 8; END_IF;
IF RunFwd OR Out_JogFwd THEN
    Out_LogicCommand := Out_LogicCommand + 16;
END_IF;
IF RunRev OR Out_JogRev THEN
    Out_LogicCommand := Out_LogicCommand + 32;
END_IF;
IF Inp_KeypadCtrlCmd THEN
    Out_LogicCommand := Out_LogicCommand + 64;
END_IF;

IF Out_JogFwd OR Out_JogRev THEN
    SpeedRef := Inp_JogSpeed;
ELSE
    SpeedRef := Out_RefSpeed;
END_IF;
IF SpeedRef < 0.0 THEN
    SpeedRef := 0.0;
ELSIF SpeedRef > Inp_MaxSpeed THEN
    SpeedRef := Inp_MaxSpeed;
END_IF;
Out_SpeedCommand := REAL_TO_INT(SpeedRef * 100.0);

Out_RunFwd := RunFwd;
Out_RunRev := RunRev;
Out_Stopping := Inp_Active AND NOT
    (RunFwd OR RunRev OR Out_JogFwd OR Out_JogRev);
"""


def build_powerflex525_iec_unit() -> IRReusableUnit:
    """Return the verified portable core as executable neutral IR."""

    parameters = tuple(
        IRParameter(name, IRDirection.INPUT, data_type)
        for name, data_type in _INPUTS
    ) + tuple(
        IRParameter(name, IRDirection.OUTPUT, data_type)
        for name, data_type in _OUTPUTS
    )
    variables = tuple(
        IRVariable(name, data_type) for name, data_type in _LOCALS
    )
    symbols = tuple(
        SemanticSymbol(
            declaration.name,
            (
                SymbolKind.PARAMETER
                if isinstance(declaration, IRParameter)
                else SymbolKind.LOCAL
            ),
            declaration.data_type,
        )
        for declaration in (*parameters, *variables)
    )
    routine = lower_structured_text(
        analyze_semantics(
            parse_structured_text(_BODY),
            SemanticContext(
                symbols=symbols,
                call_rules=(
                    CallRule(
                        "REAL_TO_INT",
                        CallKind.TYPE_CONVERSION,
                        "REAL_TO_INT",
                        minimum_arguments=1,
                        maximum_arguments=1,
                        result_type="INT",
                    ),
                ),
                conversion_policy=TypeConversionPolicy(
                    implicit_numeric=True,
                ),
            ),
        ),
        routine_name="Logic",
        role=IRRoutineRole.PRIMARY,
    )
    return IRReusableUnit(
        name="TF_PowerFlex525_Core",
        kind=IRUnitKind.FUNCTION_BLOCK,
        parameters=parameters,
        variables=variables,
        routines=(routine,),
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
    """Compose the portable drive core with CODESYS module diagnostics.

    Cyclic transport bytes remain explicit program variables; this integration
    does not fabricate native device-tree channel paths.
    """

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
        f"{module.instance_name}(\n"
        + ",\n".join(arguments)
        + "\n);"
    )
    return CodesysProjectIntegration(
        bindings=core.bindings,
        program_name=core.program_name,
        task_name=core.task_name,
        instance_name=core.instance_name,
        interval_ms=core.interval_ms,
        priority=core.priority,
        program_variables=(
            CodesysProgramVariable(
                module.instance_name,
                module_unit.name,
            ),
            *module_variables,
            *module.program_variables,
        ),
        statements_before_call=module.statements_before_call,
        statements_after_call=(
            module_call,
            *module.statements_after_call,
        ),
    )
