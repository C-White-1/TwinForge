"""Lossless-enough EDS document parsing and conservative identity lowering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import (
    Identity,
    Revision,
    SourceExtension,
    SourceNode,
    VendorIdentity,
)


@dataclass(frozen=True)
class EdsAssignment:
    """One ordered EDS assignment with its original statement text."""

    name: str
    value: str
    raw_statement: str = field(repr=False)


@dataclass(frozen=True)
class EdsSection:
    """One ordered EDS section, including duplicate assignment names."""

    name: str
    assignments: tuple[EdsAssignment, ...] = ()
    raw_lines: tuple[str, ...] = field(default=(), repr=False)

    def values(self, name: str) -> tuple[str, ...]:
        """Return all values for an assignment name, case-insensitively."""

        expected = name.casefold()
        return tuple(
            item.value
            for item in self.assignments
            if item.name.casefold() == expected
        )

    def value(self, name: str) -> str | None:
        """Return the first matching value without hiding duplicates."""

        values = self.values(name)
        return values[0] if values else None


@dataclass(frozen=True)
class EdsAssembly:
    """One EDS assembly declaration before connection-path resolution."""

    reference: str
    name: str | None
    descriptor: int | None
    declared_count: int | None
    parameter_reference: str | None
    fields: tuple[str, ...] = field(repr=False)
    raw_statement: str = field(repr=False)


@dataclass(frozen=True)
class EdsDocument:
    """One parsed EDS document and its promoted CIP identity."""

    source_path: Path
    identity: Identity
    assemblies: tuple[EdsAssembly, ...]
    sections: tuple[EdsSection, ...]
    preamble: tuple[str, ...] = field(default=(), repr=False)
    diagnostics: tuple[ConversionDiagnostic, ...] = ()

    def section(self, name: str) -> EdsSection | None:
        """Return the first section with the requested case-insensitive name."""

        expected = name.casefold()
        return next(
            (item for item in self.sections if item.name.casefold() == expected),
            None,
        )


class EDSParser:
    """Parse ODVA-style EDS text without interpreting unknown sections."""

    def __init__(self) -> None:
        self.diagnostics: list[ConversionDiagnostic] = []

    def parse(self, filename: str | Path) -> EdsDocument:
        """Parse a file and promote documented `[Device]` identity fields."""

        self.diagnostics = []
        path = Path(filename)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        preamble, sections = _parse_sections(text)
        device = _section(sections, "Device")
        identity = self._identity(device)
        assemblies = self._assemblies(_section(sections, "Assembly"))
        return EdsDocument(
            source_path=path,
            identity=identity,
            assemblies=assemblies,
            sections=sections,
            preamble=preamble,
            diagnostics=tuple(self.diagnostics),
        )

    def _assemblies(self, section: EdsSection | None) -> tuple[EdsAssembly, ...]:
        if section is None:
            return ()
        assemblies: list[EdsAssembly] = []
        for assignment in section.assignments:
            suffix = assignment.name.removeprefix("Assem")
            if not assignment.name.startswith("Assem") or not suffix.isdigit():
                continue
            fields = _fields(assignment.value)
            if len(fields) < 8:
                self._diagnostic(
                    DiagnosticSeverity.WARNING,
                    "invalid_eds_assembly",
                    (
                        f"EDS assembly {assignment.name} requires at least "
                        f"8 positional fields, got {len(fields)}"
                    ),
                    field=assignment.name,
                    raw_value=assignment.value,
                )
            assemblies.append(
                EdsAssembly(
                    reference=assignment.name,
                    name=_string(_field(fields, 0)),
                    descriptor=self._positional_integer(
                        fields,
                        3,
                        assignment.name,
                        "descriptor",
                    ),
                    declared_count=self._positional_integer(
                        fields,
                        6,
                        assignment.name,
                        "declared count",
                    ),
                    parameter_reference=_optional_text(_field(fields, 7)),
                    fields=fields,
                    raw_statement=assignment.raw_statement,
                )
            )
        return tuple(assemblies)

    def _identity(self, device: EdsSection | None) -> Identity:
        if device is None:
            self._diagnostic(
                DiagnosticSeverity.ERROR,
                "eds_device_section_missing",
                "EDS document does not contain a [Device] section",
            )
            return Identity()
        vendor_id = self._integer(device, "VendCode")
        major = self._integer(device, "MajRev")
        minor = self._integer(device, "MinRev")
        return Identity(
            vendor=(
                VendorIdentity(
                    id=vendor_id,
                    name=_string(device.value("VendName")),
                )
                if vendor_id is not None
                else None
            ),
            product_type=self._integer(device, "ProdType"),
            product_type_name=_string(device.value("ProdTypeStr")),
            product_code=self._integer(device, "ProdCode"),
            product_name=_string(device.value("ProdName")),
            revision=(
                Revision(major=major, minor=minor)
                if major is not None and minor is not None
                else None
            ),
            source_extensions=[_section_extension(device)],
        )

    def _integer(self, section: EdsSection, name: str) -> int | None:
        value = section.value(name)
        if value is None:
            return None
        try:
            return int(value.strip(), 0)
        except ValueError:
            self._diagnostic(
                DiagnosticSeverity.WARNING,
                "invalid_eds_integer",
                f"EDS [Device] {name} must be an integer, got {value!r}",
                field=name,
                raw_value=value,
            )
            return None

    def _positional_integer(
        self,
        fields: tuple[str, ...],
        index: int,
        assignment: str,
        label: str,
    ) -> int | None:
        value = _optional_text(_field(fields, index))
        if value is None:
            return None
        try:
            return int(value, 0)
        except ValueError:
            self._diagnostic(
                DiagnosticSeverity.WARNING,
                "invalid_eds_assembly_integer",
                (
                    f"EDS assembly {assignment} {label} must be an integer, "
                    f"got {value!r}"
                ),
                field=assignment,
                raw_value=value,
            )
            return None

    def _diagnostic(
        self,
        severity: DiagnosticSeverity,
        code: str,
        message: str,
        *,
        field: str | None = None,
        raw_value: str | None = None,
    ) -> None:
        self.diagnostics.append(
            ConversionDiagnostic(
                severity=severity,
                code=code,
                message=message,
                object_name="Device",
                field=field,
                raw_value=raw_value,
            )
        )


def _parse_sections(text: str) -> tuple[tuple[str, ...], tuple[EdsSection, ...]]:
    preamble: list[str] = []
    sections: list[EdsSection] = []
    section_name: str | None = None
    section_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if section_name is not None:
                sections.append(_build_section(section_name, section_lines))
            section_name = stripped[1:-1].strip()
            section_lines = []
        elif section_name is None:
            preamble.append(line)
        else:
            section_lines.append(line)
    if section_name is not None:
        sections.append(_build_section(section_name, section_lines))
    return tuple(preamble), tuple(sections)


def _build_section(name: str, lines: list[str]) -> EdsSection:
    assignments: list[EdsAssignment] = []
    statement: list[str] = []
    for line in lines:
        semantic = _without_comment(line)
        if not statement and (not semantic.strip() or "=" not in semantic):
            continue
        statement.append(line)
        if _has_terminator(semantic):
            assignment = _assignment("\n".join(statement))
            if assignment is not None:
                assignments.append(assignment)
            statement = []
    if statement:
        assignment = _assignment("\n".join(statement))
        if assignment is not None:
            assignments.append(assignment)
    return EdsSection(
        name=name,
        assignments=tuple(assignments),
        raw_lines=tuple(lines),
    )


def _assignment(raw_statement: str) -> EdsAssignment | None:
    semantic = "\n".join(_without_comment(line) for line in raw_statement.splitlines())
    if "=" not in semantic:
        return None
    name, value = semantic.split("=", 1)
    return EdsAssignment(
        name=name.strip(),
        value=value.strip().removesuffix(";").strip(),
        raw_statement=raw_statement,
    )


def _without_comment(line: str) -> str:
    quoted = False
    result: list[str] = []
    for character in line:
        if character == '"':
            quoted = not quoted
        if character == "$" and not quoted:
            break
        result.append(character)
    return "".join(result)


def _has_terminator(line: str) -> bool:
    return _without_comment(line).rstrip().endswith(";")


def _string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        return stripped[1:-1]
    return stripped


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _field(fields: tuple[str, ...], index: int) -> str | None:
    return fields[index] if index < len(fields) else None


def _fields(value: str) -> tuple[str, ...]:
    """Split EDS positional fields while retaining commas inside strings."""

    fields: list[str] = []
    current: list[str] = []
    quoted = False
    index = 0
    while index < len(value):
        character = value[index]
        if character == '"':
            if quoted and index + 1 < len(value) and value[index + 1] == '"':
                current.extend(('"', '"'))
                index += 2
                continue
            quoted = not quoted
        if character == "," and not quoted:
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        index += 1
    fields.append("".join(current).strip())
    return tuple(fields)


def _section(
    sections: tuple[EdsSection, ...],
    name: str,
) -> EdsSection | None:
    expected = name.casefold()
    return next(
        (section for section in sections if section.name.casefold() == expected),
        None,
    )


def _section_extension(section: EdsSection) -> SourceExtension:
    return SourceExtension(
        format="EDS",
        root=SourceNode(
            name=section.name,
            children=[
                SourceNode(
                    name=item.name,
                    text=item.value,
                    attributes={"raw_statement": item.raw_statement},
                )
                for item in section.assignments
            ],
        ),
    )
