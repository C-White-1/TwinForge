"""CODESYS project-integration configuration for reusable IEC IR units."""

from __future__ import annotations

from dataclasses import dataclass
import re

from twinforge.ir import IRParameter


@dataclass(frozen=True)
class CodesysArgumentBinding:
    """Bind one reusable-unit parameter to a program-local variable."""

    parameter_name: str
    variable_name: str
    dimensions: str | None = None
    initial_value: str | None = None


@dataclass(frozen=True)
class CodesysProgramVariable:
    """Declare one additional program-local variable for target integration."""

    name: str
    data_type: str
    dimensions: str | None = None
    initial_value: str | None = None


@dataclass(frozen=True)
class CodesysProgramCall:
    """Call one reusable unit instance from a generated program."""

    unit_name: str
    instance_name: str
    bindings: tuple[CodesysArgumentBinding, ...]
    statements_before_call: tuple[str, ...] = ()
    statements_after_call: tuple[str, ...] = ()


@dataclass(frozen=True)
class CodesysProjectIntegration:
    """Explicit program, call, and task configuration for reusable IR."""

    bindings: tuple[CodesysArgumentBinding, ...]
    program_name: str = "PLC_PRG"
    task_name: str = "MainTask"
    instance_name: str = "fbInstance"
    interval_ms: int = 20
    priority: int = 1
    program_variables: tuple[CodesysProgramVariable, ...] = ()
    statements_before_call: tuple[str, ...] = ()
    statements_after_call: tuple[str, ...] = ()
    calls: tuple[CodesysProgramCall, ...] = ()


def codesys_program_variable_name(parameter: IRParameter) -> str:
    """Generate a case-distinct, type-oriented program binding name."""

    prefixes = {
        "BOOL": "x",
        "DINT": "di",
        "INT": "i",
        "LINT": "li",
        "REAL": "r",
        "LREAL": "lr",
        "SINT": "si",
        "UDINT": "udi",
        "UINT": "ui",
        "ULINT": "uli",
        "USINT": "usi",
    }
    prefix = prefixes.get((parameter.data_type or "").upper(), "v")
    identifier = re.sub(r"\W+", "_", parameter.name).strip("_") or "Value"
    return f"{prefix}{identifier}"


def codesys_parameter_initial_value(
    parameter: IRParameter,
) -> str | None:
    """Translate a captured scalar default to PLCopen lexical form."""

    if parameter.default_value is not None:
        if isinstance(parameter.default_value, bool):
            return "TRUE" if parameter.default_value else "FALSE"
        return parameter.default_lexical_value
    if parameter.name.casefold() == "enablein":
        return "TRUE"
    return None
