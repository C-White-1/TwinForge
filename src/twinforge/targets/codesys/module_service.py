"""CODESYS EtherNet/IP implementation of the neutral module-service boundary.

The adapter deliberately exposes normalized CODESYS observations. It does not
convert them into Rockwell ``EntryStatus``, ``FaultCode``, ``FaultInfo``, or
``Mode`` values because the two runtimes do not share those representations.
"""

from dataclasses import dataclass
from typing import Protocol

from twinforge.runtime import ModuleStatus


@dataclass(frozen=True)
class CodesysEtherNetIPObservation:
    """Evidence available from a generated CODESYS remote-adapter object."""

    adapter_state: str
    device_state: str
    connected: bool
    enabled: bool
    faulted: bool
    diagnostic_available: bool
    diagnostic_text: str | None = None
    device_identity: str | None = None
    can_reconfigure: bool = False

    def __post_init__(self) -> None:
        if self.diagnostic_text is not None and not self.diagnostic_available:
            raise ValueError(
                "diagnostic_text requires diagnostic_available to be true"
            )


class CodesysEtherNetIPProvider(Protocol):
    """Bus-specific operations supplied by a CODESYS application binding."""

    def observe(self) -> CodesysEtherNetIPObservation:
        """Read the generated remote-adapter diagnostic IEC object."""
        ...

    def request_reconfigure(self, *, enabled: bool) -> str:
        """Start DED reconfiguration and return a correlation identifier."""
        ...


class CodesysModuleAdapterError(RuntimeError):
    """A classified inability to perform a CODESYS module operation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CodesysEtherNetIPModuleAdapter:
    """Map verified CODESYS observations to the neutral ``ModuleService``.

    This class intentionally does not implement ``SysModuleAdapter``. The
    latter requires raw Rockwell controller-object values that CODESYS does
    not expose. It instead implements the narrower normalized
    ``ModuleService`` contract.
    """

    def __init__(self, provider: CodesysEtherNetIPProvider) -> None:
        self._provider = provider

    def status(self) -> ModuleStatus:
        """Return normalized health without claiming Rockwell equivalence."""

        observation = self._provider.observe()
        diagnostic_code = _diagnostic_code(observation)
        return ModuleStatus(
            connected=observation.connected,
            enabled=observation.enabled,
            faulted=observation.faulted,
            diagnostic_code=diagnostic_code,
            diagnostic_message=observation.diagnostic_text,
        )

    def request_enabled(self, enabled: bool) -> str:
        """Request reconfiguration only when the driver reports support."""

        observation = self._provider.observe()
        if not observation.can_reconfigure:
            raise CodesysModuleAdapterError(
                "reconfigure-unsupported",
                "the CODESYS EtherNet/IP node does not report "
                "DED.CanReconfigure",
            )
        return self._provider.request_reconfigure(enabled=enabled)


def _diagnostic_code(
    observation: CodesysEtherNetIPObservation,
) -> str | None:
    """Preserve CODESYS state evidence in a stable normalized code."""

    if not observation.diagnostic_available and not observation.faulted:
        return None
    return (
        f"codesys-enip:{observation.adapter_state}:"
        f"{observation.device_state}"
    )
