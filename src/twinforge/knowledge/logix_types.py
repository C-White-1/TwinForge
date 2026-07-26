"""Evidence-backed Logix built-in structure definitions."""

from __future__ import annotations

from twinforge.structured_text import SemanticType, SemanticTypeMember


_VENDOR = "Rockwell Automation"
_TIMER_SOURCE = (
    "Studio 5000 Logix Designer Help: Timer instructions and FBD_TIMER"
)
_MESSAGE_SOURCE = "Studio 5000 Logix Designer Help: MESSAGE Structure"
_STRING_SOURCE = "Studio 5000 Logix Designer Help: String data type"


def logix_builtin_types() -> tuple[SemanticType, ...]:
    """Return immutable built-in type evidence for Logix semantic analysis."""

    return (
        _timer_type(),
        _fbd_timer_type(),
        _string_type(),
        _message_type(),
    )


def _timer_type() -> SemanticType:
    return SemanticType(
        "TIMER",
        (
            SemanticTypeMember("EN", "BOOL", "0"),
            SemanticTypeMember("TT", "BOOL", "0"),
            SemanticTypeMember("DN", "BOOL", "0"),
            SemanticTypeMember("PRE", "DINT", "0"),
            SemanticTypeMember("ACC", "DINT", "0"),
        ),
        vendor=_VENDOR,
        source=_TIMER_SOURCE,
    )


def _fbd_timer_type() -> SemanticType:
    return SemanticType(
        "FBD_TIMER",
        (
            SemanticTypeMember("EnableIn", "BOOL", "0"),
            SemanticTypeMember("TimerEnable", "BOOL", "0"),
            SemanticTypeMember("PRE", "DINT", "0"),
            SemanticTypeMember("Reset", "BOOL", "0"),
            SemanticTypeMember("EnableOut", "BOOL", "0"),
            SemanticTypeMember("ACC", "DINT", "0"),
            SemanticTypeMember("EN", "BOOL", "0"),
            SemanticTypeMember("TT", "BOOL", "0"),
            SemanticTypeMember("DN", "BOOL", "0"),
            SemanticTypeMember("Status", "DINT", "0"),
            SemanticTypeMember("InstructFault", "BOOL", "0"),
            SemanticTypeMember("PresetInv", "BOOL", "0"),
        ),
        vendor=_VENDOR,
        source=_TIMER_SOURCE,
    )


def _string_type() -> SemanticType:
    return SemanticType(
        "STRING",
        (
            SemanticTypeMember("LEN", "DINT", "0"),
            SemanticTypeMember("DATA", "SINT", "82"),
        ),
        vendor=_VENDOR,
        source=_STRING_SOURCE,
    )


def _message_type() -> SemanticType:
    return SemanticType(
        "MESSAGE",
        (
            SemanticTypeMember("Class", "INT", "0"),
            SemanticTypeMember("Instance", "DINT", "0"),
            SemanticTypeMember("Attribute", "DINT", "0"),
            SemanticTypeMember("REQ_LEN", "INT", "0"),
            SemanticTypeMember("Path", "STRING", "0"),
            SemanticTypeMember("EN", "BOOL", "0"),
            SemanticTypeMember("DN", "BOOL", "0"),
            SemanticTypeMember("ER", "BOOL", "0"),
        ),
        vendor=_VENDOR,
        source=_MESSAGE_SOURCE,
        complete=False,
    )
