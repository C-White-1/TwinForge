"""Vendor-neutral execution semantics for reusable instruction bodies."""

from __future__ import annotations

from dataclasses import replace

from twinforge.structured_text import SourceSpan

from .model import (
    IRAssignment,
    IRDiagnostic,
    IRDirection,
    IRIf,
    IRIfBranch,
    IRReference,
    IRReusableUnit,
    IRRoutineRole,
    IRUnitKind,
)


def apply_aoi_execution_semantics(unit: IRReusableUnit) -> IRReusableUnit:
    """Apply documented AOI enable behavior without target assumptions."""

    if any(
        item.code == "aoi_enable_semantics_applied"
        for item in unit.diagnostics
    ):
        return unit

    enable_in = _system_parameter(unit, "enablein", IRDirection.INPUT)
    enable_out = _system_parameter(
        unit,
        "enableout",
        IRDirection.OUTPUT,
    )
    diagnostics = list(unit.diagnostics)
    diagnostics.extend(_unmapped_lifecycle_diagnostics(unit))
    primary_index = next(
        (
            index
            for index, routine in enumerate(unit.routines)
            if routine.role is IRRoutineRole.PRIMARY
        ),
        None,
    )
    if (
        enable_in is None
        or enable_out is None
        or primary_index is None
    ):
        diagnostics.append(
            IRDiagnostic(
                "aoi_enable_interface_unavailable",
                "AOI execution semantics require system-defined EnableIn, "
                "EnableOut, and a primary routine",
                SourceSpan(0, 0),
            )
        )
        return replace(unit, diagnostics=tuple(diagnostics))

    primary = unit.routines[primary_index]
    enable_in_false = next(
        (
            routine
            for routine in unit.routines
            if routine.role is IRRoutineRole.ENABLE_IN_FALSE
        ),
        None,
    )
    span = primary.statements[0].span if primary.statements else SourceSpan(0, 0)
    propagation = IRAssignment(
        span=span,
        target=IRReference(
            span=span,
            data_type="BOOL",
            name=enable_out.name,
        ),
        value=IRReference(
            span=span,
            data_type="BOOL",
            name=enable_in.name,
        ),
    )
    guarded_logic = IRIf(
        span=span,
        branches=(
            IRIfBranch(
                span=span,
                condition=IRReference(
                    span=span,
                    data_type="BOOL",
                    name=enable_in.name,
                ),
                statements=primary.statements,
            ),
        ),
        else_statements=(
            enable_in_false.statements
            if (
                unit.lifecycle.enable_in_false_enabled
                and enable_in_false is not None
            )
            else ()
        ),
    )
    transformed_primary = replace(
        primary,
        statements=(propagation, guarded_logic),
    )
    diagnostics.extend(
        (
            IRDiagnostic(
                "default_enable_out_synthesized",
                "synthesized the documented AOI default "
                "EnableOut := EnableIn behavior",
                span,
            ),
            IRDiagnostic(
                "main_routine_guarded_by_enable_in",
                "guarded the AOI primary routine with EnableIn",
                span,
            ),
            IRDiagnostic(
                "aoi_enable_semantics_applied",
                "applied target-neutral AOI normal-scan semantics",
                span,
            ),
        )
    )
    if (
        unit.lifecycle.enable_in_false_enabled
        and enable_in_false is not None
    ):
        diagnostics.append(
            IRDiagnostic(
                "enable_in_false_mapped",
                "mapped enabled EnableInFalse logic to the false branch",
                span,
            )
        )
    routines = list(unit.routines)
    routines[primary_index] = transformed_primary
    return replace(
        unit,
        kind=IRUnitKind.FUNCTION_BLOCK,
        routines=tuple(routines),
        diagnostics=tuple(diagnostics),
    )


def _system_parameter(
    unit: IRReusableUnit,
    name: str,
    direction: IRDirection,
):
    for parameter in unit.parameters:
        if (
            parameter.system_defined
            and parameter.name.casefold() == name
            and parameter.direction is direction
        ):
            return parameter
    return None


def _unmapped_lifecycle_diagnostics(
    unit: IRReusableUnit,
) -> list[IRDiagnostic]:
    lifecycle = unit.lifecycle
    modes = (
        ("prescan", lifecycle.prescan_enabled),
        ("postscan", lifecycle.postscan_enabled),
    )
    diagnostics = [
        IRDiagnostic(
            f"{name}_mapping_required",
            f"enabled AOI {name.replace('_', ' ')} behavior is captured "
            "but requires an explicit target lifecycle mapping",
            SourceSpan(0, 0),
        )
        for name, enabled in modes
        if enabled
    ]
    if lifecycle.enable_in_false_enabled and not any(
        routine.role is IRRoutineRole.ENABLE_IN_FALSE
        for routine in unit.routines
    ):
        diagnostics.append(
            IRDiagnostic(
                "enable_in_false_mapping_required",
                "enabled AOI enable in false behavior requires a "
                "captured EnableInFalse ScanModeRoutine",
                SourceSpan(0, 0),
            )
        )
    return diagnostics
