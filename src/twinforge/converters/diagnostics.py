from dataclasses import dataclass
from enum import Enum


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ConversionDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    object_name: str | None = None
    field: str | None = None
    raw_value: str | None = None
