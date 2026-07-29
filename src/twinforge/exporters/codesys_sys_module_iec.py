"""IEC construction for the normalized CODESYS EtherNet/IP module binding."""

from __future__ import annotations

import re

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
    SemanticContext,
    SemanticSymbol,
    SymbolKind,
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

_IEC_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")

_INPUTS = (
    ("Inp_Connected", "BOOL"),
    ("Inp_Enabled", "BOOL"),
    ("Inp_Faulted", "BOOL"),
    ("Inp_DiagnosticAvailable", "BOOL"),
    ("Inp_CanReconfigure", "BOOL"),
    ("Inp_ReconfigureBusy", "BOOL"),
    ("Inp_ReconfigureDone", "BOOL"),
    ("Inp_ReconfigureFailed", "BOOL"),
    ("Inp_Inhibit", "BOOL"),
    ("Inp_Uninhibit", "BOOL"),
)
_OUTPUTS = (
    ("Out_Connected", "BOOL"),
    ("Out_Enabled", "BOOL"),
    ("Out_Faulted", "BOOL"),
    ("Out_DiagnosticAvailable", "BOOL"),
    ("Out_RequestReconfigure", "BOOL"),
    ("Out_RequestedEnable", "BOOL"),
    ("Out_ReconfigureBlocked", "BOOL"),
    ("Out_ReconfigureBusy", "BOOL"),
    ("Out_ReconfigureDone", "BOOL"),
    ("Out_ReconfigureFailed", "BOOL"),
)
_LOCALS = (("CommandLatch", "BOOL"),)

_BODY = """\
Out_Connected := Inp_Connected;
Out_Enabled := Inp_Enabled;
Out_Faulted := Inp_Faulted;
Out_DiagnosticAvailable := Inp_DiagnosticAvailable;
Out_ReconfigureBusy := Inp_ReconfigureBusy;
Out_ReconfigureDone := Inp_ReconfigureDone;
Out_ReconfigureFailed := Inp_ReconfigureFailed;
Out_RequestReconfigure := FALSE;

IF (Inp_Inhibit OR Inp_Uninhibit) AND NOT CommandLatch THEN
    IF Inp_CanReconfigure AND NOT Inp_ReconfigureBusy THEN
        Out_RequestedEnable := NOT Inp_Inhibit;
        Out_RequestReconfigure := TRUE;
        Out_ReconfigureBlocked := FALSE;
    ELSE
        Out_ReconfigureBlocked := TRUE;
    END_IF;
END_IF;

IF Inp_ReconfigureDone THEN
    Out_ReconfigureBlocked := FALSE;
END_IF;

CommandLatch := Inp_Inhibit OR Inp_Uninhibit;
"""


def build_codesys_sys_module_binding_unit() -> IRReusableUnit:
    """Return the normalized, device-object-independent binding as IEC IR."""

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
            SemanticContext(symbols=symbols),
        ),
        routine_name="Logic",
        role=IRRoutineRole.PRIMARY,
    )
    return IRReusableUnit(
        name="TF_Codesys_ENIP_ModuleBinding",
        kind=IRUnitKind.FUNCTION_BLOCK,
        parameters=parameters,
        variables=variables,
        routines=(routine,),
    )


def codesys_sys_module_binding_integration(
    device_variable: str | None = None,
) -> CodesysProjectIntegration:
    """Return a runnable program and task around the normalized binding.

    When ``device_variable`` names a generated CODESYS ``RemoteAdapter_diag``
    object, the program also observes its state and performs the verified
    single-call DED reconfiguration handshake. Without it, the result remains
    the portable binding test shell.
    """

    unit = build_codesys_sys_module_binding_unit()
    integration = CodesysProjectIntegration(
        instance_name="fbModuleBinding",
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
    if device_variable is None:
        return integration
    if _IEC_IDENTIFIER.fullmatch(device_variable) is None:
        raise ValueError(
            "device_variable must be a simple IEC 61131-3 identifier"
        )
    return CodesysProjectIntegration(
        bindings=integration.bindings,
        instance_name=integration.instance_name,
        interval_ms=integration.interval_ms,
        program_variables=(
            CodesysProgramVariable("fbReconfigure", "DED.Reconfigure"),
            CodesysProgramVariable("xObservedEnabled", "BOOL"),
            CodesysProgramVariable(
                "xObservedDiagnosticAvailable",
                "BOOL",
            ),
            CodesysProgramVariable(
                "sObservedDiagnostic",
                "STRING(255)",
            ),
            CodesysProgramVariable(
                "eObservedDeviceState",
                "DED.DEVICE_STATE",
            ),
            CodesysProgramVariable(
                "eObservedReconfigureError",
                "DED.ERROR",
            ),
        ),
        statements_before_call=(
            f"""\
xObservedEnabled := {device_variable}.Enable;
xObservedDiagnosticAvailable := \
{device_variable}.xDiagnosticAvailable;
sObservedDiagnostic := {device_variable}.sDiagString;
eObservedDeviceState := {device_variable}.GetDeviceState();

xInp_CanReconfigure := DED.CanReconfigure(
    itfNode := {device_variable}
);

xInp_Connected :=
    ({device_variable}.eState = \
IoDrvEtherNetIP.AdapterState.RUNNING)
    AND
    (eObservedDeviceState = DED.DEVICE_STATE.RUNNING);
xInp_Enabled := {device_variable}.Enable;
xInp_Faulted :=
    ({device_variable}.eState = \
IoDrvEtherNetIP.AdapterState.BUS_ERROR)
    OR
    ({device_variable}.eState = IoDrvEtherNetIP.AdapterState.ERROR)
    OR
    (eObservedDeviceState = DED.DEVICE_STATE.ERROR);
xInp_DiagnosticAvailable := \
{device_variable}.xDiagnosticAvailable;
xInp_ReconfigureBusy := fbReconfigure.xBusy;
xInp_ReconfigureDone := fbReconfigure.xDone;
xInp_ReconfigureFailed := fbReconfigure.xError;
eObservedReconfigureError := fbReconfigure.eError;""",
        ),
        statements_after_call=(
            f"""\
IF xOut_RequestReconfigure THEN
    {device_variable}.Enable := xOut_RequestedEnable;
END_IF;

fbReconfigure(
    xExecute := xOut_RequestReconfigure,
    itfNode := {device_variable}
);""",
        ),
    )
