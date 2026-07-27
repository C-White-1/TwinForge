"""Target-neutral scan logic retained from the Dvc_PF525 AOI.

This module contains no Logix MESSAGE, MODULE, GSV/SSV, wall-clock, CODESYS,
or OpenPLC API calls. Target adapters supply status and consume the returned
cyclic command values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PowerFlexCommandSource(str, Enum):
    """Selected command owner reported by the surrounding device object."""

    NONE = "none"
    PROGRAM = "program"
    OPERATOR = "operator"
    EXTERNAL = "external"
    OVERRIDE = "override"
    MAINTENANCE = "maintenance"
    LOCAL = "local"


@dataclass(frozen=True)
class PowerFlexCommands:
    """Commands and speed setpoint supplied by one command owner."""

    run_forward: bool = False
    run_reverse: bool = False
    jog_forward: bool = False
    jog_reverse: bool = False
    stop: bool = False
    reset: bool = False
    speed_hz: float = 0.0


@dataclass(frozen=True)
class PowerFlexCoreInput:
    """Complete target-neutral input for one deterministic core scan."""

    source: PowerFlexCommandSource = PowerFlexCommandSource.NONE
    program: PowerFlexCommands = field(default_factory=PowerFlexCommands)
    operator: PowerFlexCommands = field(default_factory=PowerFlexCommands)
    external: PowerFlexCommands = field(default_factory=PowerFlexCommands)
    maintenance: PowerFlexCommands = field(default_factory=PowerFlexCommands)
    override_command: int = 0
    override_speed_hz: float = 0.0
    program_override_active: bool = False
    maintenance_program_speed_hz: float = 0.0
    permissive_ok: bool = True
    non_bypassable_permissive_ok: bool = True
    interlock_ok: bool = True
    non_bypassable_interlock_ok: bool = True
    bypass_active: bool = False
    run_forward_available: bool = True
    run_reverse_available: bool = True
    jog_forward_available: bool = True
    jog_reverse_available: bool = True
    drive_ready: bool = False
    drive_active: bool = False
    ethernet_logic_control: bool = False
    keypad_control_status: bool = False
    keypad_control_command: bool = False
    maximum_speed_hz: float = 0.0
    jog_speed_hz: float = 0.0
    start_delay_ms: int = 0
    elapsed_ms: int = 0

    def __post_init__(self) -> None:
        if self.start_delay_ms < 0:
            raise ValueError("start_delay_ms must not be negative")
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms must not be negative")


@dataclass(frozen=True)
class PowerFlexCoreOutput:
    """Cyclic command values and observable portable status."""

    logic_command: int
    speed_command: int
    reference_speed_hz: float
    permissives_ok: bool
    interlocks_ok: bool
    run_forward: bool
    run_reverse: bool
    jog_forward: bool
    jog_reverse: bool
    starting: bool
    stopping: bool

    def cyclic_values(self) -> dict[str, int | bool]:
        """Return values accepted by the captured command-image layout."""

        return {
            "LogicCommand": self.logic_command,
            "SpeedCommand": self.speed_command,
        }


@dataclass
class PowerFlexCoreState:
    """Retained values corresponding to stateful AOI local tags."""

    run_forward: bool = False
    run_reverse: bool = False
    start_elapsed_ms: int = 0
    override_command: int = 0

    def reset(self) -> None:
        """Explicitly clear state when required by a target/project policy."""

        self.run_forward = False
        self.run_reverse = False
        self.start_elapsed_ms = 0
        self.override_command = 0


class PowerFlex525Core:
    """Execute the target-neutral command portion of Dvc_PF525."""

    def __init__(self, state: PowerFlexCoreState | None = None) -> None:
        self.state = state or PowerFlexCoreState()

    def prescan(self) -> None:
        """Apply the captured Prescan effect on portable core state.

        The AOI Prescan routine clears initialization and read-sequence state
        owned by the adapter/orchestration layer. It does not explicitly
        write these portable run or timer values, so they are preserved.
        """

    def scan(self, inputs: PowerFlexCoreInput) -> PowerFlexCoreOutput:
        """Evaluate one scan using captured AOI ordering and latch semantics."""

        permissives_ok = (
            inputs.permissive_ok or inputs.bypass_active
        ) and inputs.non_bypassable_permissive_ok
        # The source AOI comments fault, Ethernet-control, and safety terms
        # out of this equation. PF525-QA-020 tracks manual verification.
        interlocks_ok = (
            inputs.interlock_ok or inputs.bypass_active
        ) and inputs.non_bypassable_interlock_ok

        reference_speed = self._apply_source_commands(
            inputs,
            permissives_ok=permissives_ok,
            interlocks_ok=interlocks_ok,
        )
        jog_forward, jog_reverse = _jog_commands(inputs, permissives_ok)
        requested = (
            self.state.run_forward
            or self.state.run_reverse
            or jog_forward
            or jog_reverse
        )
        run_requested = self.state.run_forward or self.state.run_reverse
        timer_done, timer_timing = self._update_start_timer(
            run_requested,
            inputs.start_delay_ms,
            inputs.elapsed_ms,
        )
        stop = (
            inputs.drive_active
            and inputs.ethernet_logic_control
            and not (
                inputs.keypad_control_status
                or self.state.run_forward
                or self.state.run_reverse
                or jog_forward
                or jog_reverse
            )
        )
        start = (
            inputs.drive_ready and timer_done and not stop and requested
        )
        jog = (
            inputs.drive_ready
            and not (stop or self.state.run_forward or self.state.run_reverse)
            and (jog_forward or jog_reverse)
        )
        reset = any(
            commands.reset
            for commands in (
                inputs.program,
                inputs.operator,
                inputs.maintenance,
                inputs.external,
            )
        )
        logic_command = _logic_command(
            stop=stop,
            start=start,
            jog=jog,
            clear_fault=reset,
            forward=self.state.run_forward or jog_forward,
            reverse=self.state.run_reverse or jog_reverse,
            keypad_control=inputs.keypad_control_command,
        )
        speed_reference = (
            inputs.jog_speed_hz
            if jog_forward or jog_reverse
            else reference_speed
        )
        speed_command = _speed_command(
            speed_reference,
            inputs.maximum_speed_hz,
        )
        return PowerFlexCoreOutput(
            logic_command=logic_command,
            speed_command=speed_command,
            reference_speed_hz=reference_speed,
            permissives_ok=permissives_ok,
            interlocks_ok=interlocks_ok,
            run_forward=self.state.run_forward,
            run_reverse=self.state.run_reverse,
            jog_forward=jog_forward,
            jog_reverse=jog_reverse,
            starting=timer_timing,
            stopping=inputs.drive_active and not requested,
        )

    def _apply_source_commands(
        self,
        inputs: PowerFlexCoreInput,
        *,
        permissives_ok: bool,
        interlocks_ok: bool,
    ) -> float:
        source = inputs.source
        if source is PowerFlexCommandSource.PROGRAM:
            reference = (
                inputs.maintenance_program_speed_hz
                if inputs.program_override_active
                else inputs.program.speed_hz
            )
            self.state.run_forward = (
                inputs.program.run_forward
                and (permissives_ok or self.state.run_forward)
                and interlocks_ok
                and not inputs.program.stop
            )
            self.state.run_reverse = (
                inputs.program.run_reverse
                and (permissives_ok or self.state.run_reverse)
                and interlocks_ok
                and not inputs.program.stop
            )
            return reference
        if source is PowerFlexCommandSource.OVERRIDE:
            self.state.override_command = inputs.override_command
            command = self.state.override_command
            if command == 1 or not interlocks_ok:
                self.state.run_forward = False
                self.state.run_reverse = False
            elif command == 2 and permissives_ok:
                self.state.run_reverse = False
                self.state.run_forward = True
            elif command == 3 and permissives_ok:
                self.state.run_forward = False
                self.state.run_reverse = True
            self.state.override_command = 0
            return inputs.override_speed_hz
        commands = _selected_commands(inputs)
        if commands is None:
            self.state.run_forward = False
            self.state.run_reverse = False
            return 0.0
        self.state.run_forward = (
            self.state.run_forward
            or (
                commands.run_forward
                and inputs.run_forward_available
                and permissives_ok
                and not commands.run_reverse
            )
        ) and interlocks_ok and not commands.stop
        self.state.run_reverse = (
            self.state.run_reverse
            or (
                commands.run_reverse
                and inputs.run_reverse_available
                and permissives_ok
                and not commands.run_forward
            )
        ) and interlocks_ok and not commands.stop
        return commands.speed_hz

    def _update_start_timer(
        self,
        run_requested: bool,
        preset_ms: int,
        elapsed_ms: int,
    ) -> tuple[bool, bool]:
        if not run_requested:
            self.state.start_elapsed_ms = 0
            return False, False
        self.state.start_elapsed_ms = min(
            preset_ms,
            self.state.start_elapsed_ms + elapsed_ms,
        )
        done = self.state.start_elapsed_ms >= preset_ms
        return done, not done


def _selected_commands(
    inputs: PowerFlexCoreInput,
) -> PowerFlexCommands | None:
    return {
        PowerFlexCommandSource.OPERATOR: inputs.operator,
        PowerFlexCommandSource.EXTERNAL: inputs.external,
        PowerFlexCommandSource.MAINTENANCE: inputs.maintenance,
    }.get(inputs.source)


def _jog_commands(
    inputs: PowerFlexCoreInput,
    permissives_ok: bool,
) -> tuple[bool, bool]:
    selected = _selected_commands(inputs)
    jog_forward = (
        inputs.jog_forward_available
        and permissives_ok
        and selected is not None
        and selected.jog_forward
        and not selected.jog_reverse
    ) or (
        inputs.source is PowerFlexCommandSource.PROGRAM
        and inputs.program.jog_forward
        and not inputs.program.jog_reverse
    )
    jog_reverse = (
        inputs.jog_reverse_available
        and permissives_ok
        and selected is not None
        and selected.jog_reverse
        and not selected.jog_forward
    ) or (
        inputs.source is PowerFlexCommandSource.PROGRAM
        and inputs.program.jog_reverse
        and not inputs.program.jog_forward
    )
    return jog_forward, jog_reverse


def _logic_command(
    *,
    stop: bool,
    start: bool,
    jog: bool,
    clear_fault: bool,
    forward: bool,
    reverse: bool,
    keypad_control: bool,
) -> int:
    values = (
        stop,
        start,
        jog,
        clear_fault,
        forward,
        reverse,
        keypad_control,
    )
    return sum(1 << bit for bit, value in enumerate(values) if value) & 0x007F


def _speed_command(speed_hz: float, maximum_speed_hz: float) -> int:
    bounded = min(max(speed_hz, 0.0), maximum_speed_hz)
    # Logix assignment from REAL to INT truncates toward zero.
    return int(bounded * 100.0)
