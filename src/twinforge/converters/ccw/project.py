"""Lower validated CCW interchange evidence into neutral TwinForge models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.interchange import CCWProjectArtifact
from twinforge.model import (
    Controller,
    Identity,
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderPosition,
    LadderRung,
    LadderSeries,
    Program,
    Routine,
    SourceExtension,
    SourceNode,
    Tag,
)

_OPERATIONS = {
    "XIC": LadderOperation.NORMALLY_OPEN_CONTACT,
    "XIO": LadderOperation.NORMALLY_CLOSED_CONTACT,
    "OTE": LadderOperation.COIL,
    "OTS": LadderOperation.SET_COIL,
    "OTU": LadderOperation.RESET_COIL,
    "OTR": LadderOperation.RESET_COIL,
}


@dataclass(frozen=True)
class CCWProjectLoweringResult:
    """Neutral model plus all source and lowering diagnostics."""

    controller: Controller
    artifact: CCWProjectArtifact
    diagnostics: tuple[ConversionDiagnostic, ...]
    converted_instruction_count: int
    unsupported_instruction_count: int


class _Lowerer:
    def __init__(self, artifact: CCWProjectArtifact) -> None:
        self.artifact = artifact
        self.document = artifact.to_document()
        self.diagnostics: list[ConversionDiagnostic] = []
        self.converted_instruction_count = 0
        self.unsupported_instruction_count = 0

    def lower(self) -> CCWProjectLoweringResult:
        project_name = self.document["project"]["name"]
        controller = Controller(
            name=project_name or self.artifact.source_reference,
            identity=Identity(),
            source_extensions=[
                _extension("CCWProject", self.document, full_document=True)
            ],
        )
        for variable in self.document["variables"]:
            self._add_variable(controller, variable)
        for program_source in self.document["programs"]:
            self._add_program(controller, program_source)
        self._source_diagnostics()
        return CCWProjectLoweringResult(
            controller=controller,
            artifact=self.artifact,
            diagnostics=tuple(self.diagnostics),
            converted_instruction_count=self.converted_instruction_count,
            unsupported_instruction_count=self.unsupported_instruction_count,
        )

    def _add_variable(
        self,
        controller: Controller,
        source: dict[str, Any],
    ) -> None:
        tag = Tag(
            name=source["name"],
            tag_type="Base",
            data_type=source["data_type"],
            description=_variable_description(source),
            metadata={
                "ccw_scope": source["scope"],
                "ccw_classification": source["classification"],
                "aliases": list(source["aliases"]),
                "physical_source": source["physical_source"],
                "physical_destination": source["physical_destination"],
                "evidence_entries": list(source["evidence_entries"]),
                "usages": list(source["usages"]),
                "seal_in_rungs": list(source["seal_in_rungs"]),
            },
            source_extensions=[_extension("Variable", source)],
        )
        try:
            controller.add_tag(tag)
        except ValueError:
            self._diagnostic(
                "duplicate_ccw_variable",
                f"duplicate CCW variable {tag.name!r} was dropped; only the "
                "first variable with this name is represented in the "
                "neutral model",
                tag.name,
                severity=DiagnosticSeverity.ERROR,
            )

    def _add_program(
        self,
        controller: Controller,
        source: dict[str, Any],
    ) -> None:
        name = source["name"]
        if name in controller.programs:
            self._diagnostic(
                "duplicate_ccw_program",
                f"duplicate CCW program {name!r} was dropped; only the "
                "first program with this name is represented in the "
                "neutral model",
                name,
                severity=DiagnosticSeverity.ERROR,
            )
            return
        program = Program(
            name=name,
            source_extensions=[_extension("Program", source)],
        )
        routine = Routine(
            name=name,
            language=source["language"],
            metadata={"source_entry": source["source_entry"]},
            source_extensions=[_extension("ProgramBody", source)],
        )
        for rung_source in source["rungs"]:
            routine.ladder_rungs.append(self._rung(rung_source))
        for message in source["diagnostics"]:
            self._diagnostic(
                "ccw_program_diagnostic",
                str(message),
                name,
                severity=DiagnosticSeverity.WARNING,
            )
        program.add_routine(routine)
        controller.add_program(program)

    def _rung(self, source: dict[str, Any]) -> LadderRung:
        return LadderRung(
            number=source["number"],
            position=_position(source["position"]),
            network=self._series(source["network"]),
            source_sha256=source["raw_sha256"],
            source_extensions=[_extension("Rung", source)],
        )

    def _series(self, source: dict[str, Any]) -> LadderSeries:
        elements: list[LadderInstruction | LadderParallel] = []
        for element in source["elements"]:
            if element["kind"] == "parallel":
                elements.append(
                    LadderParallel(
                        branches=tuple(
                            self._series(branch) for branch in element["branches"]
                        )
                    )
                )
            else:
                elements.append(self._instruction(element))
        return LadderSeries(tuple(elements))

    def _instruction(self, source: dict[str, Any]) -> LadderInstruction:
        mnemonic = source["mnemonic"]
        operation = _OPERATIONS.get(mnemonic, LadderOperation.UNSUPPORTED)
        if operation is LadderOperation.UNSUPPORTED:
            self.unsupported_instruction_count += 1
            self._diagnostic(
                "unsupported_ccw_instruction",
                f"CCW instruction {mnemonic!r} has no neutral lowering",
                source.get("operand"),
                raw_value=mnemonic,
                severity=DiagnosticSeverity.WARNING,
            )
        else:
            self.converted_instruction_count += 1
        return LadderInstruction(
            operation=operation,
            source_mnemonic=mnemonic,
            operand=source["operand"],
            alias=source["alias"],
            annotations=tuple(source["annotations"]),
            position=_position(source["position"]),
        )

    def _source_diagnostics(self) -> None:
        for message in self.document["diagnostics"]:
            self._diagnostic(
                "ccw_source_diagnostic",
                str(message),
                None,
                severity=DiagnosticSeverity.WARNING,
            )
        for operand in self.document["unresolved_operands"]:
            self._diagnostic(
                "ccw_unresolved_operand",
                f"CCW source could not resolve operand {operand!r}",
                str(operand),
                severity=DiagnosticSeverity.WARNING,
            )

    def _diagnostic(
        self,
        code: str,
        message: str,
        object_name: str | None,
        *,
        severity: DiagnosticSeverity,
        raw_value: str | None = None,
    ) -> None:
        self.diagnostics.append(
            ConversionDiagnostic(
                severity=severity,
                code=code,
                message=message,
                object_name=object_name,
                raw_value=raw_value,
            )
        )


def lower_ccw_project(artifact: CCWProjectArtifact) -> CCWProjectLoweringResult:
    """Lower one validated artifact without making target-specific decisions."""

    return _Lowerer(artifact).lower()


def _variable_description(source: dict[str, Any]) -> str | None:
    aliases = source["aliases"]
    return ", ".join(aliases) if aliases else None


def _position(source: dict[str, Any] | None) -> LadderPosition | None:
    if source is None:
        return None
    return LadderPosition(column=source["column"], row=source["row"])


def _extension(
    name: str,
    evidence: dict[str, Any],
    *,
    full_document: bool = False,
) -> SourceExtension:
    attributes = {"schema_version": "ccw-project-v1"}
    if "name" in evidence and evidence["name"] is not None:
        attributes["name"] = str(evidence["name"])
    return SourceExtension(
        format="ccw-project-v1",
        root=SourceNode(name=name, attributes=attributes),
        metadata={
            "document" if full_document else "evidence": evidence,
        },
    )
