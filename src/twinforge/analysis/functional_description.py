"""Assemble evidence-backed functional descriptions for device logic."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.model import AddOnInstruction, Device

from .cyclic_io import CyclicIOContract
from .diagnostic_report import DeviceDiagnosticReport


@dataclass(frozen=True)
class OperatingModeDescription:
    """One command-source mode and its observed control behavior."""

    name: str
    status_parameter: str
    speed_source: str
    command_behavior: str


@dataclass(frozen=True)
class FunctionalBehaviorDescription:
    """One cohesive behavior with direct Structured Text evidence."""

    name: str
    description: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class DeviceFunctionalDescription:
    """Engineering description assembled from controller-source evidence."""

    device_name: str
    device_model: str | None
    implementation_name: str
    purpose: str
    modes: tuple[OperatingModeDescription, ...]
    behaviors: tuple[FunctionalBehaviorDescription, ...]
    cyclic_io: CyclicIOContract
    diagnostics: DeviceDiagnosticReport
    observed_parameter_count: int
    boundaries: tuple[str, ...]


def build_device_functional_description(
    device: Device,
    implementation: AddOnInstruction,
    cyclic_io: CyclicIOContract,
    diagnostics: DeviceDiagnosticReport,
) -> DeviceFunctionalDescription:
    """Describe observed behavior without asserting unverified plant intent."""

    source = "\n".join(
        routine.structured_text
        for routine in implementation.iter_routines()
        if routine.structured_text
    )
    return DeviceFunctionalDescription(
        device_name=device.name,
        device_model=device.model,
        implementation_name=implementation.name,
        purpose=(
            "Provide multi-source command arbitration, permissive and "
            "interlock gating, speed-reference handling, cyclic EtherNet/IP "
            "control, parameter access, and diagnostics for a variable-speed "
            "drive."
        ),
        modes=_modes(implementation),
        behaviors=(
            _behavior(
                "Initialization",
                (
                    "Inhibition or an initialize command while stopped clears "
                    "initialized status. While uninitialized, local status and "
                    "edge-triggered command storage are reset. Initialization "
                    "is restored after the parameter-read sequence completes."
                ),
                source,
                "if (Sts_Inhibited OR",
                "if (NOT Sts_Initialized) then",
                "Sts_Initialized := 1;",
            ),
            _behavior(
                "Permissives and interlocks",
                (
                    "Bypass may satisfy the bypassable permissive and "
                    "interlock inputs. Non-bypassable permissives and "
                    "interlocks always remain required. The executed "
                    "interlock expression does not include the fault, "
                    "EtherNet/IP logic-control, or safety-active terms shown "
                    "inside its source comment."
                ),
                source,
                "PermOK :=",
                "IntlkOK :=",
                "Sts_Bypass :=",
            ),
            _behavior(
                "Run and jog commands",
                (
                    "Forward and reverse are mutually selected. Program run "
                    "commands are level-triggered; operator, external, and "
                    "maintenance starts are latched edge-style and require a "
                    "separate stop. Jog commands require availability and "
                    "permissive conditions."
                ),
                source,
                "RunFwd := PCmd_RunFwd",
                "RunFwd := (RunFwd OR (OCmd_RunFwd",
                "JogFwd :=",
            ),
            _behavior(
                "Start delay and audible request",
                (
                    "A validated 0–60 second start delay is converted to "
                    "milliseconds. Starting status follows timer timing, and "
                    "the drive Start bit is withheld until the timer is done. "
                    "When maintenance has enabled it, the audible request is "
                    "active during the starting interval."
                ),
                source,
                "StartTimer.PRE := Cfg_StartDelay * 1000;",
                "Local.DataOut.Start :=",
                "Out_Audible := Sts_AudibleEnabled & Sts_Starting;",
            ),
            _behavior(
                "Speed reference",
                (
                    "The active command-source mode selects the speed "
                    "reference. Jogging uses the configured jog speed. "
                    "Negative requests are forced to zero, requests above "
                    "maximum speed are limited, and the transmitted reference "
                    "uses 0.01 Hz/count."
                ),
                source,
                "RefSpeed := PSet_Speed;",
                "Local.DataOut.SpeedCommand := RefSpeed * 100;",
                "Local.DataOut.SpeedCommand := Val_JogSpeed * 100;",
            ),
            _behavior(
                "Setpoint tracking",
                (
                    "When set tracking is enabled, program mode tracks the "
                    "operator setpoint from the active reference. Local mode "
                    "tracks both operator and program setpoints from the "
                    "reported command speed. The apparent operator-to-program "
                    "tracking assignment is commented out."
                ),
                source,
                "if (Cfg_SetTrack) then",
                "OSet_Speed := RefSpeed;",
                "PSet_Speed := Val_CmdSpeed;",
            ),
            _behavior(
                "Parameter services",
                (
                    "Cyclic operation is supplemented by explicit CIP reads "
                    "and writes. Reads are enabled only while the module is "
                    "connected and rotate through eight read sequences. "
                    "Configured setpoints are compared with process values "
                    "before individual writes are requested."
                ),
                source,
                "PG.Inp_Enable := Module.Sts_Connected;",
                "if (ReadSeq > 7) then",
                "if (Sts_Initialized & PG.Out) then",
            ),
        ),
        cyclic_io=cyclic_io,
        diagnostics=diagnostics,
        observed_parameter_count=len(device.observed_parameters),
        boundaries=(
            "This describes captured controller logic, not the complete "
            "mechanical, electrical, or process safety design.",
            "The AOI asserts that a safety function exists and derives "
            "SafetyActive from drive status, but no safety integrity claim "
            "can be made from L5X logic alone.",
            "The commented fault, EtherNet/IP-control, and safety terms in "
            "IntlkOK require manual design verification; see PF525-QA-020.",
            "Hardware behavior, parameter acceptance, timing, and network-loss "
            "response remain subject to commissioning tests.",
        ),
    )


def _modes(
    implementation: AddOnInstruction,
) -> tuple[OperatingModeDescription, ...]:
    definitions = (
        (
            "Program",
            "Sts_Program",
            "PSet_Speed, or MSet_PSet while program-setpoint override is active",
            "Level-triggered run; program stop removes the run request.",
        ),
        (
            "Operator",
            "Sts_Operator",
            "OSet_Speed",
            "Latched run request from operator commands; separate stop required.",
        ),
        (
            "External",
            "Sts_External",
            "XSet_Speed",
            "Latched run request from external commands; separate stop required.",
        ),
        (
            "Override",
            "Sts_Override",
            "OvSet_Speed",
            "One encoded command selects no change, stop, forward, or reverse.",
        ),
        (
            "Maintenance",
            "Sts_Maintenance",
            "MSet_Speed",
            "Latched maintenance run plus bypass and service commands.",
        ),
        (
            "Local or disabled",
            "Sts_Local / Sts_Disabled",
            "Drive-local source or no host reference",
            "Host run and reverse requests are cleared by the fallback branch.",
        ),
    )
    available = {name.casefold() for name in implementation.parameters}
    return tuple(
        OperatingModeDescription(*item)
        for item in definitions
        if all(
            part.casefold() in available
            for part in item[1].split(" / ")
        )
    )


def _behavior(
    name: str,
    description: str,
    source: str,
    *needles: str,
) -> FunctionalBehaviorDescription:
    lines = source.splitlines()
    evidence = tuple(
        line.strip()
        for needle in needles
        for line in lines
        if needle in line
    )
    return FunctionalBehaviorDescription(
        name=name,
        description=description,
        evidence=tuple(dict.fromkeys(evidence)),
    )
