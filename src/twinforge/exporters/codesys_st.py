"""CODESYS-specific rendering of executable IR as IEC Structured Text."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.ir import IRDirection, IRReusableUnit, IRRoutine

from .iec_st import IECSTEmission, emit_iec_st_routine, emit_iec_st_unit


@dataclass(frozen=True)
class CodesysSTDialect:
    """Map neutral IEC requirements to supported CODESYS constructs."""

    def render_array_dimension(
        self,
        array: str,
        dimension: str,
    ) -> str:
        """Render zero-based SIZE semantics using one-based CODESYS bounds."""

        target_dimension = f"({dimension} + 1)"
        return (
            f"((UPPER_BOUND({array}, {target_dimension}) - "
            f"LOWER_BOUND({array}, {target_dimension})) + 1)"
        )

    def supports_generic_array_interface(
        self,
        direction: IRDirection,
    ) -> bool:
        """CODESYS supports variable arrays in ``VAR_IN_OUT``."""

        return direction is IRDirection.INOUT


_CODESYS_DIALECT = CodesysSTDialect()


def emit_codesys_st_unit(unit: IRReusableUnit) -> IECSTEmission:
    """Emit a reusable unit with known CODESYS requirements resolved."""

    return emit_iec_st_unit(unit, _CODESYS_DIALECT)


def emit_codesys_st_routine(routine: IRRoutine) -> IECSTEmission:
    """Emit one routine with known CODESYS requirements resolved."""

    return emit_iec_st_routine(routine, _CODESYS_DIALECT)
