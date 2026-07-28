"""Runtime orchestration for the vendor-neutral ``Sys_Module`` core.

This module defines the boundary between deterministic AOI behavior and an
external module-service implementation. A concrete adapter may use CODESYS,
EtherNet/IP, a simulator, or another transport without changing the core.
"""

from dataclasses import dataclass
from typing import Protocol

from .sys_module_core import (
    SysModuleCore,
    SysModuleModeWrite,
    SysModuleOutputs,
    SysModulePrescanResult,
    SysModuleSnapshot,
)


class SysModuleAdapter(Protocol):
    """Read module state and apply requested Mode writes."""

    def read_snapshot(self) -> SysModuleSnapshot:
        """Return the current module attributes required by ``Sys_Module``."""
        ...

    def write_mode(self, mode: int) -> None:
        """Write the module Mode attribute or raise ``SysModuleAdapterError``."""
        ...


class SysModuleAdapterError(RuntimeError):
    """A classified failure reported by a concrete module-service adapter."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SysModuleServiceFailure:
    """Transport-independent evidence of an adapter operation failure."""

    code: str
    message: str


@dataclass(frozen=True)
class SysModuleRuntimeResult:
    """Observable result of one coordinated runtime cycle."""

    outputs: SysModuleOutputs
    mode_write: SysModuleModeWrite | None = None
    read_failure: SysModuleServiceFailure | None = None
    write_failure: SysModuleServiceFailure | None = None


class SysModuleRuntime:
    """Coordinate the pure ``Sys_Module`` core with an external adapter.

    Read failures do not scan the core, so they neither change outputs nor
    consume an input edge. Failed writes are reported but are not retried
    automatically: retry requires the source command to return false and then
    produce another rising edge, matching the retained one-shot semantics.
    """

    def __init__(
        self,
        adapter: SysModuleAdapter,
        core: SysModuleCore | None = None,
    ) -> None:
        self._adapter = adapter
        self._core = core if core is not None else SysModuleCore()

    def cycle(
        self,
        *,
        input_inhibit: bool = False,
        input_uninhibit: bool = False,
    ) -> SysModuleRuntimeResult:
        """Read, scan, and apply at most one Mode write."""

        try:
            snapshot = self._adapter.read_snapshot()
        except SysModuleAdapterError as error:
            return SysModuleRuntimeResult(
                outputs=self._core.outputs,
                read_failure=_failure_from(error),
            )

        scan = self._core.scan(
            snapshot,
            input_inhibit=input_inhibit,
            input_uninhibit=input_uninhibit,
        )
        if scan.mode_write is None:
            return SysModuleRuntimeResult(outputs=scan.outputs)

        try:
            self._adapter.write_mode(scan.mode_write.mode)
        except SysModuleAdapterError as error:
            return SysModuleRuntimeResult(
                outputs=scan.outputs,
                mode_write=scan.mode_write,
                write_failure=_failure_from(error),
            )

        return SysModuleRuntimeResult(
            outputs=scan.outputs,
            mode_write=scan.mode_write,
        )

    def prescan(self) -> SysModulePrescanResult:
        """Apply the source AOI Prescan behavior without adapter operations."""

        return self._core.prescan()


def _failure_from(error: SysModuleAdapterError) -> SysModuleServiceFailure:
    """Convert adapter-specific exception flow into result evidence."""

    return SysModuleServiceFailure(code=error.code, message=str(error))
