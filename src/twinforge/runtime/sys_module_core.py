"""Portable source semantics for the captured Rockwell ``Sys_Module`` AOI."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SysModuleSnapshot:
    """Raw values read from one controller-managed module object."""

    instance: int = 0
    entry_status: int = 0
    fault_code: int = 0
    fault_info: int = 0
    mode: int = 0


@dataclass(frozen=True)
class SysModuleStatus:
    """Decoded status aliases exposed by the source AOI."""

    standby: bool = False
    faulted: bool = False
    validating: bool = False
    connecting: bool = False
    connected: bool = False
    shutting_down: bool = False
    inhibited: bool = False
    waiting: bool = False
    firmware_updating: bool = False
    configuring: bool = False
    disconnected: bool = False

    @property
    def word(self) -> int:
        """Return the Rockwell alias-compatible status bit word."""
        values = (
            (0, self.standby),
            (1, self.faulted),
            (2, self.validating),
            (3, self.connecting),
            (4, self.connected),
            (5, self.shutting_down),
            (6, self.inhibited),
            (7, self.waiting),
            (9, self.firmware_updating),
            (10, self.configuring),
            (11, self.disconnected),
        )
        return sum(1 << bit for bit, enabled in values if enabled)


@dataclass(frozen=True)
class SysModuleOutputs:
    """Raw diagnostic outputs and decoded status from one scan."""

    snapshot: SysModuleSnapshot = SysModuleSnapshot()
    status: SysModuleStatus = SysModuleStatus()


@dataclass(frozen=True)
class SysModuleModeWrite:
    """One source-equivalent SSV Mode write intent."""

    mode: int


@dataclass(frozen=True)
class SysModuleScanResult:
    """Outputs and optional mode-write intent produced by a cyclic scan."""

    outputs: SysModuleOutputs
    mode_write: SysModuleModeWrite | None = None


@dataclass(frozen=True)
class SysModulePrescanResult:
    """Source values after the AOI Prescan routine."""

    outputs: SysModuleOutputs
    input_inhibit: bool = False
    input_uninhibit: bool = False


class SysModuleCore:
    """Execute portable AOI logic while retaining the source shared OSR."""

    def __init__(self) -> None:
        self._osr = False
        self.outputs = SysModuleOutputs()

    def scan(
        self,
        snapshot: SysModuleSnapshot,
        *,
        input_inhibit: bool = False,
        input_uninhibit: bool = False,
    ) -> SysModuleScanResult:
        """Decode status and produce at most one rising-edge Mode write."""
        mode_write: SysModuleModeWrite | None = None
        if input_inhibit and not self._osr:
            mode_write = SysModuleModeWrite(snapshot.mode | 0x0004)
        elif input_uninhibit and not self._osr:
            mode_write = SysModuleModeWrite(snapshot.mode & 0xFFFB)
        self._osr = input_inhibit or input_uninhibit
        self.outputs = SysModuleOutputs(
            snapshot=snapshot,
            status=decode_entry_status(snapshot.entry_status),
        )
        return SysModuleScanResult(self.outputs, mode_write)

    def prescan(self) -> SysModulePrescanResult:
        """Apply only assignments explicitly present in source Prescan.

        The source clears both command inputs, the Status word, and diagnostic
        outputs. It does not assign the retained ``OSR`` local tag.
        """
        self.outputs = SysModuleOutputs()
        return SysModulePrescanResult(outputs=self.outputs)


def decode_entry_status(entry_status: int) -> SysModuleStatus:
    """Decode the high status nibble exactly as the source AOI does."""
    state = entry_status & 0xF000
    inhibited = state == 0x6000
    connected = state == 0x4000
    return SysModuleStatus(
        standby=state == 0x0000,
        faulted=state == 0x1000,
        validating=state == 0x2000,
        connecting=state == 0x3000,
        connected=connected,
        shutting_down=state == 0x5000,
        inhibited=inhibited,
        waiting=state == 0x7000,
        firmware_updating=state == 0x9000,
        configuring=state == 0xA000,
        disconnected=not (inhibited or connected),
    )
