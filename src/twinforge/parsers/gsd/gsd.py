"""Lossless-enough PROFIBUS GSD parsing and conservative metadata promotion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity


@dataclass(frozen=True)
class GsdAssignment:
    """One ordered GSD assignment with its original source line."""

    name: str
    value: str
    raw_line: str = field(repr=False)


@dataclass(frozen=True)
class GsdIdentity:
    """Identity fields stated by a PROFIBUS GSD file."""

    vendor_name: str | None = None
    model_name: str | None = None
    revision: str | None = None
    ident_number: int | None = None
    protocol_ident: int | None = None
    station_type: int | None = None
    hardware_release: str | None = None
    software_release: str | None = None


@dataclass(frozen=True)
class GsdLimits:
    """Declared station limits; absent values remain unknown."""

    max_modules: int | None = None
    max_input_length: int | None = None
    max_output_length: int | None = None
    max_data_length: int | None = None
    max_diagnostic_data_length: int | None = None
    max_user_parameter_data_length: int | None = None
    minimum_slave_interval: int | None = None


@dataclass(frozen=True)
class GsdDocument:
    """Parsed GSD evidence and promoted identity and limit fields."""

    source_path: Path
    identity: GsdIdentity
    limits: GsdLimits
    assignments: tuple[GsdAssignment, ...]
    directives: tuple[str, ...]
    raw_lines: tuple[str, ...] = field(repr=False)
    diagnostics: tuple[ConversionDiagnostic, ...] = ()

    def values(self, name: str) -> tuple[str, ...]:
        """Return all matching assignment values, case-insensitively."""

        expected = name.casefold()
        return tuple(
            item.value
            for item in self.assignments
            if item.name.casefold() == expected
        )

    def value(self, name: str) -> str | None:
        """Return the first value while leaving duplicates accessible."""

        values = self.values(name)
        return values[0] if values else None


class GSDParser:
    """Parse GSD text without discarding unknown keywords or source lines."""

    def __init__(self) -> None:
        self.diagnostics: list[ConversionDiagnostic] = []

    def parse(self, filename: str | Path) -> GsdDocument:
        """Parse one GSD file and promote documented station metadata."""

        self.diagnostics = []
        path = Path(filename)
        text = path.read_text(encoding="latin-1")
        raw_lines = tuple(text.splitlines())
        assignments = _assignments(raw_lines)
        directives = tuple(
            semantic.strip()
            for line in raw_lines
            if (semantic := _without_comment(line)).strip().startswith("#")
        )
        document = GsdDocument(
            source_path=path,
            identity=GsdIdentity(),
            limits=GsdLimits(),
            assignments=assignments,
            directives=directives,
            raw_lines=raw_lines,
        )
        identity = GsdIdentity(
            vendor_name=_string(document.value("Vendor_Name")),
            model_name=_string(document.value("Model_Name")),
            revision=_string(document.value("Revision")),
            ident_number=self._integer(document, "Ident_Number"),
            protocol_ident=self._integer(document, "Protocol_Ident"),
            station_type=self._integer(document, "Station_Type"),
            hardware_release=_string(document.value("Hardware_Release")),
            software_release=_string(document.value("Software_Release")),
        )
        limits = GsdLimits(
            max_modules=self._integer(document, "Max_Module"),
            max_input_length=self._integer(document, "Max_Input_Len"),
            max_output_length=self._integer(document, "Max_Output_Len"),
            max_data_length=self._integer(document, "Max_Data_Len"),
            max_diagnostic_data_length=self._integer(
                document, "Max_Diag_Data_Len"
            ),
            max_user_parameter_data_length=self._integer(
                document, "Max_User_Prm_Data_Len"
            ),
            minimum_slave_interval=self._integer(
                document, "Min_Slave_Intervall"
            ),
        )
        return GsdDocument(
            source_path=path,
            identity=identity,
            limits=limits,
            assignments=assignments,
            directives=directives,
            raw_lines=raw_lines,
            diagnostics=tuple(self.diagnostics),
        )

    def _integer(self, document: GsdDocument, name: str) -> int | None:
        value = document.value(name)
        if value is None:
            return None
        try:
            return int(value.strip(), 0)
        except ValueError:
            self.diagnostics.append(
                ConversionDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="invalid_gsd_integer",
                    message=f"GSD {name} must be an integer, got {value!r}",
                    object_name="Station",
                    field=name,
                    raw_value=value,
                )
            )
            return None


def _assignments(lines: tuple[str, ...]) -> tuple[GsdAssignment, ...]:
    assignments: list[GsdAssignment] = []
    for line in lines:
        semantic = _without_comment(line).strip()
        if not semantic or semantic.startswith("#") or "=" not in semantic:
            continue
        name, value = semantic.split("=", 1)
        assignments.append(
            GsdAssignment(
                name=name.strip(),
                value=value.strip(),
                raw_line=line,
            )
        )
    return tuple(assignments)


def _without_comment(line: str) -> str:
    quoted = False
    result: list[str] = []
    for character in line:
        if character == '"':
            quoted = not quoted
        if character == ";" and not quoted:
            break
        result.append(character)
    return "".join(result)


def _string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        return stripped[1:-1]
    return stripped
