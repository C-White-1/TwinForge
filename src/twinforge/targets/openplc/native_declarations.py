"""Declare native OpenPLC variables and compatibility function blocks."""

from __future__ import annotations

from pathlib import Path

from twinforge.model import Program

from .counter import TF_COUNTER_SOURCE
from .native_errors import OpenPLCNativeUnsupportedError


TF_RTO_BODY = """Enabled := IN;

IF RESET THEN
    SegmentTimer(IN := FALSE, PT := T#0s);
    RetainedTime := T#0s;
    RemainingTime := T#0s;
    ET := T#0s;
    Q := FALSE;
    Enabled := FALSE;
    TT := FALSE;
    WasEnabled := FALSE;
ELSIF IN AND NOT Q THEN
    IF RetainedTime >= PT THEN
        RetainedTime := PT;
        ET := PT;
        Q := TRUE;
        TT := FALSE;
        SegmentTimer(IN := FALSE, PT := T#0s);
    ELSE
        RemainingTime := PT - RetainedTime;
        SegmentTimer(IN := TRUE, PT := RemainingTime);
        ET := RetainedTime + SegmentTimer.ET;
        IF SegmentTimer.Q THEN
            RetainedTime := PT;
            ET := PT;
            Q := TRUE;
        END_IF;
        TT := NOT Q;
    END_IF;
ELSIF NOT IN THEN
    IF WasEnabled AND NOT Q THEN
        RetainedTime := RetainedTime + SegmentTimer.ET;
        IF RetainedTime >= PT THEN
            RetainedTime := PT;
            Q := TRUE;
        END_IF;
    END_IF;
    SegmentTimer(IN := FALSE, PT := T#0s);
    ET := RetainedTime;
    TT := FALSE;
ELSE
    SegmentTimer(IN := FALSE, PT := T#0s);
    ET := RetainedTime;
    TT := FALSE;
END_IF;

WasEnabled := IN;"""
TF_RTO_SOURCE = f"""FUNCTION_BLOCK TF_RTO
VAR_INPUT
    IN : BOOL;
    RESET : BOOL;
    PT : TIME;
END_VAR

VAR_OUTPUT
    Q : BOOL;
    ET : TIME;
    Enabled : BOOL;
    TT : BOOL;
END_VAR

VAR
    SegmentTimer : TON;
    RetainedTime : TIME := T#0s;
    RemainingTime : TIME := T#0s;
    WasEnabled : BOOL := FALSE;
END_VAR

{TF_RTO_BODY}

END_FUNCTION_BLOCK
"""
def variable_declaration(
    name: str,
    data_type: str | None,
    location: str | None,
    timer_type: str,
    shared_counter: bool,
) -> str:
    """Render one evidenced native OpenPLC local declaration."""

    if (data_type or "").upper() == "TIMER":
        native_type = "TF_RTO" if timer_type == "RTO" else timer_type
        return f"\t{name} : {native_type};"
    if (data_type or "").upper() == "COUNTER":
        if not shared_counter:
            raise OpenPLCNativeUnsupportedError(
                f"COUNTER {name!r} has no supported canonical instruction group"
            )
        return f"\t{name} : TF_COUNTER;"
    if location is None:
        return f"\t{name} : BOOL;"
    return f"\t{name} : bool AT {location};"


def counter_names(program: Program) -> set[str]:
    """Return local Rockwell COUNTER tags visible to native lowering."""

    return {
        tag.name
        for tag in program.iter_tags()
        if (tag.data_type or "").upper() == "COUNTER"
    }


def compatibility_block_documents(
    timer_types: dict[str, str],
    shared_counter_names: set[str],
) -> dict[Path, str]:
    """Return compatibility function blocks required by the lowered program."""

    documents: dict[Path, str] = {}
    if "RTO" in timer_types.values():
        documents[Path("pous/function-blocks/TF_RTO.st")] = TF_RTO_SOURCE
    if shared_counter_names:
        documents[Path("pous/function-blocks/TF_COUNTER.st")] = TF_COUNTER_SOURCE
    return documents
