"""Classify implementation work needed to convert a reusable instruction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .aoi import AOIPortabilityFinding
from .cyclic_io import CyclicIOContract
from .diagnostic_report import DeviceDiagnosticReport


class ConversionDisposition(str, Enum):
    """Implementation disposition for one conversion work item."""

    DIRECT_PORTABLE = "direct_portable"
    TYPE_ADAPTATION = "type_adaptation"
    TARGET_ADAPTER = "target_adapter"
    MANUAL_REVIEW = "manual_review"
    HARDWARE_VALIDATION = "hardware_validation"


@dataclass(frozen=True)
class ConversionReadinessItem:
    """One bounded conversion concern and its evidence."""

    area: str
    disposition: ConversionDisposition
    implementation_action: str
    evidence: tuple[str, ...]
    completion_criterion: str


@dataclass(frozen=True)
class DependencyReadiness:
    """Disposition of one captured AOI dependency."""

    name: str
    disposition: ConversionDisposition
    action: str


@dataclass(frozen=True)
class ConversionReadinessReport:
    """Actionable readiness matrix for one reusable implementation."""

    implementation_name: str
    recommended_pou: str
    source_disposition: str
    unresolved_dependency_count: int
    unanalyzed_routine_count: int
    items: tuple[ConversionReadinessItem, ...]
    dependencies: tuple[DependencyReadiness, ...]
    recommended_order: tuple[str, ...]


def build_conversion_readiness_report(
    finding: AOIPortabilityFinding,
    cyclic_io: CyclicIOContract,
    diagnostics: DeviceDiagnosticReport,
) -> ConversionReadinessReport:
    """Turn portability evidence into a conservative implementation plan."""

    items = (
        ConversionReadinessItem(
            area="Core command and speed logic",
            disposition=ConversionDisposition.DIRECT_PORTABLE,
            implementation_action=(
                "Lower command arbitration, permissive/interlock equations, "
                "run/jog latches, start timing, speed limiting, and tracking "
                "to vendor-neutral executable IR and IEC Structured Text."
            ),
            evidence=(
                "all implementation routines are captured as Structured Text",
                "no unresolved AOI dependencies",
            ),
            completion_criterion=(
                "IEC unit tests reproduce the captured equations and state "
                "transitions without target services."
            ),
        ),
        ConversionReadinessItem(
            area="Cyclic I/O datatypes",
            disposition=ConversionDisposition.TYPE_ADAPTATION,
            implementation_action=(
                "Replace generated Logix module datatypes with neutral status "
                "and command structures while preserving byte and bit layout."
            ),
            evidence=(
                f"input point {cyclic_io.input_image.connection_point}, "
                f"{cyclic_io.input_image.configured_size_bytes} bytes",
                f"output point {cyclic_io.output_image.connection_point}, "
                f"{cyclic_io.output_image.configured_size_bytes} bytes",
            ),
            completion_criterion=(
                "Round-trip layout tests prove every status and command field "
                "occupies the documented byte and bit position."
            ),
        ),
        ConversionReadinessItem(
            area="Rockwell data operations",
            disposition=ConversionDisposition.TYPE_ADAPTATION,
            implementation_action=(
                "Lower COP, SIZE, SWPB, TONR, and Logix bit overlays to typed "
                "IEC operations with explicit endian and bounds behavior."
            ),
            evidence=tuple(
                item
                for item in finding.structured_text_calls
                if item.upper() in {"COP", "SIZE", "SWPB", "TONR"}
            ),
            completion_criterion=(
                "Golden-vector tests cover copy length, array bounds, byte "
                "order, timer state, and signed 16-bit conversions."
            ),
        ),
        ConversionReadinessItem(
            area="Lifecycle behavior",
            disposition=ConversionDisposition.TYPE_ADAPTATION,
            implementation_action=(
                "Map the captured Prescan initialization and read-sequence "
                "resets while preserving run/timer state unless an explicit "
                "target lifecycle policy requires otherwise."
            ),
            evidence=finding.lifecycle_hooks,
            completion_criterion=(
                "Cold start, warm restart, disabled execution, and re-enable "
                "tests match the retained-state contract."
            ),
        ),
        ConversionReadinessItem(
            area="Explicit parameter messaging",
            disposition=ConversionDisposition.TARGET_ADAPTER,
            implementation_action=(
                "Define a neutral parameter read/write service and implement "
                "separate CODESYS and future OpenPLC providers."
            ),
            evidence=("MESSAGE datatype", "MSG service", "CIP class 0x93"),
            completion_criterion=(
                "A mock provider passes deterministic read/write sequencing "
                "tests before any target-specific network implementation."
            ),
        ),
        ConversionReadinessItem(
            area="Module identity, status, and inhibit services",
            disposition=ConversionDisposition.TARGET_ADAPTER,
            implementation_action=(
                "Bind the neutral module-service contract to target-specific "
                "connection diagnostics and supported control operations."
            ),
            evidence=(
                "MODULE datatype",
                "Sys_Module GSV/SSV",
                f"{len(diagnostics.indicators)} diagnostic indicators",
            ),
            completion_criterion=(
                "Each source property is classified equivalent, approximated, "
                "unavailable, or blocking for the selected target."
            ),
        ),
        ConversionReadinessItem(
            area="Wall-clock pulse generation",
            disposition=ConversionDisposition.TARGET_ADAPTER,
            implementation_action=(
                "Use the validated RTC_PulseGen target implementation behind "
                "a neutral pulse/timing contract."
            ),
            evidence=("RTC_PulseGen dependency", "wall_clock_read capability"),
            completion_criterion=(
                "Target trace confirms pulse interval and restart behavior."
            ),
        ),
        ConversionReadinessItem(
            area="Functional and safety intent",
            disposition=ConversionDisposition.MANUAL_REVIEW,
            implementation_action=(
                "Resolve open AOI QA findings before claiming semantic "
                "equivalence, especially the commented IntlkOK conditions."
            ),
            evidence=(
                "PF525-QA-020",
                "PF525-QA-021",
                "no PLCopen Common Behaviour match",
            ),
            completion_criterion=(
                "The responsible engineer records the intended interlock and "
                "safety behavior without silently changing source semantics."
            ),
        ),
        ConversionReadinessItem(
            area="Drive and network behavior",
            disposition=ConversionDisposition.HARDWARE_VALIDATION,
            implementation_action=(
                "Commission against a PowerFlex 525 or approved test setup, "
                "including cyclic control, faults, C143/C144, explicit "
                "parameters, recovery, and inhibit behavior."
            ),
            evidence=(
                "offline L5X evidence only",
                "no physical PowerFlex 525 currently available",
            ),
            completion_criterion=(
                "A signed test record demonstrates safe behavior in normal "
                "and abnormal operating states."
            ),
        ),
    )
    return ConversionReadinessReport(
        implementation_name=finding.name,
        recommended_pou=finding.recommended_pou.value,
        source_disposition=finding.disposition.value,
        unresolved_dependency_count=len(finding.unresolved_dependencies),
        unanalyzed_routine_count=len(finding.unanalyzed_routines),
        items=items,
        dependencies=_dependencies(finding),
        recommended_order=(
            "Freeze the neutral interfaces and datatype layouts.",
            "Port and unit-test the core function-block logic.",
            "Implement instruction and lifecycle adaptations.",
            "Implement a mock parameter-service and module-service adapter.",
            "Generate and compile the PLCopen/CODESYS project.",
            "Run target-runtime integration tests.",
            "Complete manual design review and hardware commissioning.",
        ),
    )


def _dependencies(
    finding: AOIPortabilityFinding,
) -> tuple[DependencyReadiness, ...]:
    actions = {
        "Math_Epsilon": (
            ConversionDisposition.DIRECT_PORTABLE,
            "Emit as portable IEC helper logic.",
        ),
        "Str_Size": (
            ConversionDisposition.DIRECT_PORTABLE,
            "Lower through the existing array-bounds translation.",
        ),
        "Op_CmdSrc": (
            ConversionDisposition.TYPE_ADAPTATION,
            "Port stateful arbitration and map Prescan explicitly.",
        ),
        "RTC_PulseGen": (
            ConversionDisposition.TARGET_ADAPTER,
            "Reuse the validated target clock implementation.",
        ),
        "Sys_Dvc": (
            ConversionDisposition.TARGET_ADAPTER,
            "Separate portable device status from controller-object metadata.",
        ),
        "Sys_Module": (
            ConversionDisposition.TARGET_ADAPTER,
            "Bind the neutral module-service contract.",
        ),
        "Msg_SetParams": (
            ConversionDisposition.TARGET_ADAPTER,
            "Replace MESSAGE mutation with neutral request construction.",
        ),
        "Msg_SetPathToModule": (
            ConversionDisposition.TARGET_ADAPTER,
            "Move routing and module-path resolution into the target provider.",
        ),
        "ST_Dvc_PF525": (
            ConversionDisposition.TYPE_ADAPTATION,
            "Emit neutral nested drive data structures.",
        ),
        "ST_Sys_DeviceClass": (
            ConversionDisposition.TYPE_ADAPTATION,
            "Emit the captured classification structure or a neutral mapping.",
        ),
    }
    result: list[DependencyReadiness] = []
    for dependency in finding.dependencies:
        _, name = dependency.split(":", 1)
        disposition, action = actions.get(
            name,
            (
                ConversionDisposition.MANUAL_REVIEW,
                "Classify this dependency before conversion.",
            ),
        )
        result.append(
            DependencyReadiness(
                name=name,
                disposition=disposition,
                action=action,
            )
        )
    return tuple(result)
