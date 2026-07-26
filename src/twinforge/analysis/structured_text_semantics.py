"""Controller-model scopes and declarative semantics for Structured Text."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from twinforge.model import (
    AddOnInstruction,
    Controller,
    Datatype,
    Program,
    Routine,
    Tag,
)
from twinforge.knowledge.logix_types import logix_builtin_types
from twinforge.structured_text import (
    AccessStatus,
    CallKind,
    CallParameter,
    CallRule,
    ReferenceStatus,
    SemanticContext,
    SemanticSymbol,
    SemanticType,
    SemanticTypeMember,
    StructuredTextSemantics,
    SymbolKind,
    TypeStatus,
    TypeCompatibility,
    TypeConversionPolicy,
    analyze_semantics,
    parse_structured_text,
)


_SOURCE_CALL_RULES = (
    CallRule(
        "SIZE",
        CallKind.ARRAY_DIMENSION_QUERY,
        "array_dimension_query",
        vendor="Rockwell Automation",
        minimum_arguments=3,
        maximum_arguments=3,
    ),
    CallRule(
        "GSV",
        CallKind.CONTROLLER_OBJECT_READ,
        "controller_object_read",
        vendor="Rockwell Automation",
        opaque_argument_indices=frozenset({0, 1, 2}),
        minimum_arguments=4,
        maximum_arguments=4,
    ),
    CallRule(
        "SSV",
        CallKind.CONTROLLER_OBJECT_WRITE,
        "controller_object_write",
        vendor="Rockwell Automation",
        opaque_argument_indices=frozenset({0, 1, 2}),
        minimum_arguments=4,
        maximum_arguments=4,
    ),
    CallRule(
        "ABS",
        CallKind.ABSOLUTE_VALUE,
        "absolute_value",
        minimum_arguments=1,
        maximum_arguments=1,
        result_from_argument=0,
    ),
    CallRule(
        "COP",
        CallKind.MEMORY_COPY,
        "memory_copy",
        vendor="Rockwell Automation",
        minimum_arguments=3,
        maximum_arguments=3,
    ),
    CallRule(
        "MSG",
        CallKind.EXPLICIT_MESSAGE,
        "explicit_message",
        vendor="Rockwell Automation",
        minimum_arguments=1,
        maximum_arguments=1,
    ),
    CallRule(
        "SWPB",
        CallKind.BYTE_SWAP,
        "byte_swap",
        vendor="Rockwell Automation",
        opaque_argument_indices=frozenset({1}),
        minimum_arguments=3,
        maximum_arguments=3,
    ),
    CallRule(
        "TONR",
        CallKind.RETENTIVE_TIMER,
        "retentive_timer",
        vendor="Rockwell Automation",
        minimum_arguments=1,
        maximum_arguments=1,
    ),
)

_LOGIX_CONVERSION_POLICY = TypeConversionPolicy(
    implicit_numeric=True,
    bit_bool_equivalent=True,
    implicit_numeric_boolean=True,
    string_family_compatible=True,
)


@dataclass(frozen=True)
class StructuredTextSemanticFinding:
    """Semantic result for one captured ST routine."""

    owner: str
    routine: str
    semantics: StructuredTextSemantics

    @property
    def resolved_references(self) -> int:
        return sum(
            item.status is ReferenceStatus.RESOLVED
            for item in self.semantics.references
        )

    @property
    def unresolved_references(self) -> int:
        return sum(
            item.status is ReferenceStatus.UNRESOLVED
            for item in self.semantics.references
        )

    @property
    def resolved_accesses(self) -> int:
        return sum(
            item.status is AccessStatus.RESOLVED
            for item in self.semantics.accesses
        )

    @property
    def unverified_accesses(self) -> int:
        return sum(
            item.status is AccessStatus.UNVERIFIED
            for item in self.semantics.accesses
        )

    @property
    def invalid_accesses(self) -> int:
        return sum(
            item.status is AccessStatus.INVALID
            for item in self.semantics.accesses
        )

    @property
    def typed_expressions(self) -> int:
        return sum(
            item.status is TypeStatus.KNOWN
            for item in self.semantics.expression_types
        )

    @property
    def incompatible_assignments(self) -> int:
        return sum(
            item.compatibility is TypeCompatibility.INCOMPATIBLE
            for item in self.semantics.assignments
        )

    @property
    def incompatible_arguments(self) -> int:
        return sum(
            binding.compatibility is TypeCompatibility.INCOMPATIBLE
            for call in self.semantics.calls
            for binding in call.bindings
        )


@dataclass(frozen=True)
class StructuredTextSemanticReport:
    """Controller-wide symbol and call resolution results."""

    controller_name: str
    routines: tuple[StructuredTextSemanticFinding, ...]

    @property
    def resolved_references(self) -> int:
        return sum(item.resolved_references for item in self.routines)

    @property
    def unresolved_references(self) -> int:
        return sum(item.unresolved_references for item in self.routines)

    @property
    def unknown_calls(self) -> int:
        return sum(
            call.kind is CallKind.UNKNOWN
            for finding in self.routines
            for call in finding.semantics.calls
        )

    @property
    def resolved_accesses(self) -> int:
        return sum(item.resolved_accesses for item in self.routines)

    @property
    def unverified_accesses(self) -> int:
        return sum(item.unverified_accesses for item in self.routines)

    @property
    def invalid_accesses(self) -> int:
        return sum(item.invalid_accesses for item in self.routines)

    @property
    def typed_expressions(self) -> int:
        return sum(item.typed_expressions for item in self.routines)

    @property
    def invalid_signatures(self) -> int:
        return sum(
            call.signature_valid is False
            for finding in self.routines
            for call in finding.semantics.calls
        )

    @property
    def incompatible_assignments(self) -> int:
        return sum(
            item.incompatible_assignments for item in self.routines
        )

    @property
    def incompatible_arguments(self) -> int:
        return sum(
            item.incompatible_arguments for item in self.routines
        )

    def assignment_compatibility(
        self,
        compatibility: TypeCompatibility,
    ) -> int:
        """Count assignments with one compatibility outcome."""

        return sum(
            item.compatibility is compatibility
            for finding in self.routines
            for item in finding.semantics.assignments
        )

    def argument_compatibility(
        self,
        compatibility: TypeCompatibility,
    ) -> int:
        """Count bound call arguments with one compatibility outcome."""

        return sum(
            binding.compatibility is compatibility
            for finding in self.routines
            for call in finding.semantics.calls
            for binding in call.bindings
        )

    def render_text(self) -> str:
        """Render deterministic resolution evidence."""

        lines = [
            f"Structured Text semantics: {self.controller_name}",
            f"Routines: {len(self.routines)}",
            f"Resolved references: {self.resolved_references}",
            f"Unresolved references: {self.unresolved_references}",
            f"Unknown calls: {self.unknown_calls}",
            f"Resolved member/index accesses: {self.resolved_accesses}",
            f"Unverified member/index accesses: {self.unverified_accesses}",
            f"Invalid member/index accesses: {self.invalid_accesses}",
            f"Typed expressions: {self.typed_expressions}",
            f"Invalid mapped signatures: {self.invalid_signatures}",
            f"Incompatible assignments: {self.incompatible_assignments}",
            f"Incompatible bound arguments: {self.incompatible_arguments}",
            "Assignment compatibility: "
            f"{self._compatibility_text(self.assignment_compatibility)}",
            "Bound argument compatibility: "
            f"{self._compatibility_text(self.argument_compatibility)}",
        ]
        for finding in self.routines:
            lines.extend(
                [
                    "",
                    f"Routine: {finding.owner}/{finding.routine}",
                    f"  Resolved references: {finding.resolved_references}",
                    f"  Unresolved references: {finding.unresolved_references}",
                    f"  Calls: {len(finding.semantics.calls)}",
                    f"  Resolved accesses: {finding.resolved_accesses}",
                    f"  Unverified accesses: {finding.unverified_accesses}",
                    f"  Invalid accesses: {finding.invalid_accesses}",
                    f"  Typed expressions: {finding.typed_expressions}",
                    "  Incompatible assignments: "
                    f"{finding.incompatible_assignments}",
                    "  Incompatible bound arguments: "
                    f"{finding.incompatible_arguments}",
                    f"  Diagnostics: {len(finding.semantics.diagnostics)}",
                ]
            )
            for call in finding.semantics.calls:
                vendor = f", vendor={call.vendor}" if call.vendor else ""
                lines.append(
                    f"    - {call.source_name}({call.argument_count} args): "
                    f"{call.kind.value}"
                    f" -> {call.neutral_name}{vendor}"
                )
            for diagnostic in finding.semantics.diagnostics:
                lines.append(
                    f"    ! {diagnostic.code} "
                    f"[{diagnostic.span.start}:{diagnostic.span.end}]: "
                    f"{diagnostic.message}"
                )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _compatibility_text(
        counter: Callable[[TypeCompatibility], int],
    ) -> str:
        values = [
            f"{item.value}={counter(item)}"
            for item in TypeCompatibility
        ]
        return ", ".join(values)


def analyze_structured_text_semantics(
    controller: Controller,
) -> StructuredTextSemanticReport:
    """Resolve all captured ST routines against their model scopes."""

    findings: list[StructuredTextSemanticFinding] = []
    controller_symbols = tuple(
        _tag_symbol(tag, SymbolKind.CONTROLLER_TAG, "Controller")
        for tag in controller.iter_tags()
    )
    shared_rules = _call_rules(controller)
    types = _semantic_types(controller)
    for instruction in sorted(
        controller.add_on_instructions.values(),
        key=lambda item: item.name.casefold(),
    ):
        context = SemanticContext(
            symbols=controller_symbols + _aoi_symbols(instruction),
            types=types,
            call_rules=shared_rules,
            conversion_policy=_LOGIX_CONVERSION_POLICY,
        )
        findings.extend(
            _findings(
                f"AOI:{instruction.name}",
                instruction.iter_routines(),
                context,
            )
        )
    for program in sorted(
        controller.iter_programs(),
        key=lambda item: item.name.casefold(),
    ):
        context = SemanticContext(
            symbols=controller_symbols + _program_symbols(program),
            types=types,
            call_rules=shared_rules + _routine_rules(program),
            conversion_policy=_LOGIX_CONVERSION_POLICY,
        )
        findings.extend(
            _findings(
                f"Program:{program.name}",
                program.iter_routines(),
                context,
            )
        )
    return StructuredTextSemanticReport(controller.name, tuple(findings))


def _findings(
    owner: str,
    routines: Iterable[Routine],
    context: SemanticContext,
) -> list[StructuredTextSemanticFinding]:
    findings: list[StructuredTextSemanticFinding] = []
    for routine in sorted(routines, key=lambda item: item.name.casefold()):
        if (routine.language or "").casefold() not in {"st", "structuredtext"}:
            continue
        semantics = analyze_semantics(
            parse_structured_text(routine.structured_text),
            context,
        )
        findings.append(
            StructuredTextSemanticFinding(owner, routine.name, semantics)
        )
    return findings


def _tag_symbol(
    tag: Tag,
    kind: SymbolKind,
    scope: str,
) -> SemanticSymbol:
    return SemanticSymbol(
        tag.name,
        kind,
        tag.data_type,
        scope,
        tag.dimensions,
    )


def _aoi_symbols(
    instruction: AddOnInstruction,
) -> tuple[SemanticSymbol, ...]:
    parameters = tuple(
        SemanticSymbol(
            item.name,
            SymbolKind.PARAMETER,
            item.effective_data_type,
            f"AOI:{instruction.name}",
            item.dimensions,
        )
        for item in instruction.parameters.values()
    )
    locals_ = tuple(
        _tag_symbol(
            item,
            SymbolKind.LOCAL,
            f"AOI:{instruction.name}",
        )
        for item in instruction.local_tags.values()
    )
    return parameters + locals_


def _program_symbols(program: Program) -> tuple[SemanticSymbol, ...]:
    return tuple(
        _tag_symbol(tag, SymbolKind.PROGRAM_TAG, f"Program:{program.name}")
        for tag in program.iter_tags()
    )


def _call_rules(controller: Controller) -> tuple[CallRule, ...]:
    aoi_rules = tuple(
        _aoi_call_rule(instruction)
        for instruction in controller.add_on_instructions.values()
    )
    return _SOURCE_CALL_RULES + aoi_rules


def _aoi_call_rule(instruction: AddOnInstruction) -> CallRule:
    required = tuple(
        CallParameter(
            parameter.name,
            parameter.data_type,
            parameter.usage,
            parameter.dimensions,
            generic_dimensions=parameter.dimensions is not None,
        )
        for parameter in instruction.parameters.values()
        if parameter.required is True
        and parameter.name.casefold() not in {"enablein", "enableout"}
    )
    count = 1 + len(required)
    return CallRule(
        instruction.name,
        CallKind.USER_DEFINED_INSTRUCTION,
        instruction.name,
        minimum_arguments=count,
        maximum_arguments=count,
        instance_data_type=instruction.name,
        parameters=required,
    )


def _routine_rules(program: Program) -> tuple[CallRule, ...]:
    return tuple(
        CallRule(routine.name, CallKind.ROUTINE, routine.name)
        for routine in program.iter_routines()
    )


def _semantic_types(
    controller: Controller,
) -> tuple[SemanticType, ...]:
    captured = tuple(
        _semantic_type(datatype)
        for datatype in controller.datatypes.values()
    )
    aoi_instances = tuple(
        _aoi_semantic_type(instruction)
        for instruction in controller.add_on_instructions.values()
    )
    return logix_builtin_types() + aoi_instances + captured


def _semantic_type(datatype: Datatype) -> SemanticType:
    return SemanticType(
        datatype.name,
        tuple(
            SemanticTypeMember(
                member.name,
                member.data_type_name,
                member.dimension,
            )
            for member in datatype.members
        ),
        source="L5X controller data-type definition",
    )


def _aoi_semantic_type(
    instruction: AddOnInstruction,
) -> SemanticType:
    return SemanticType(
        instruction.name,
        tuple(
            SemanticTypeMember(
                parameter.name,
                parameter.data_type,
                parameter.dimensions,
            )
            for parameter in instruction.parameters.values()
            if (parameter.usage or "").casefold() != "inout"
        ),
        vendor=instruction.vendor,
        source="L5X Add-On Instruction parameter definition",
        complete=False,
    )
