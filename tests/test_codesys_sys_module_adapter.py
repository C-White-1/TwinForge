from dataclasses import dataclass, field

import pytest

from twinforge.runtime import ModuleService
from twinforge.targets.codesys import (
    CodesysEtherNetIPModuleAdapter,
    CodesysEtherNetIPObservation,
    CodesysModuleAdapterError,
)


@dataclass
class FakeCodesysProvider:
    observation: CodesysEtherNetIPObservation
    requests: list[bool] = field(default_factory=list)

    def observe(self) -> CodesysEtherNetIPObservation:
        return self.observation

    def request_reconfigure(self, *, enabled: bool) -> str:
        self.requests.append(enabled)
        return f"reconfigure-{len(self.requests)}"


def observation(
    *,
    connected: bool = True,
    enabled: bool = True,
    faulted: bool = False,
    diagnostic_available: bool = False,
    diagnostic_text: str | None = None,
    can_reconfigure: bool = False,
) -> CodesysEtherNetIPObservation:
    return CodesysEtherNetIPObservation(
        adapter_state="running" if connected else "not-running",
        device_state="operational" if connected else "not-found",
        connected=connected,
        enabled=enabled,
        faulted=faulted,
        diagnostic_available=diagnostic_available,
        diagnostic_text=diagnostic_text,
        device_identity="PowerFlex 525 example",
        can_reconfigure=can_reconfigure,
    )


def test_adapter_structurally_satisfies_neutral_module_service():
    adapter: ModuleService = CodesysEtherNetIPModuleAdapter(
        FakeCodesysProvider(observation())
    )

    assert adapter.status().connected


def test_status_maps_normalized_health_without_diagnostic_invention():
    adapter = CodesysEtherNetIPModuleAdapter(
        FakeCodesysProvider(observation())
    )

    status = adapter.status()

    assert status.connected
    assert status.enabled
    assert not status.faulted
    assert status.diagnostic_code is None
    assert status.diagnostic_message is None


def test_status_preserves_codesys_diagnostic_evidence():
    adapter = CodesysEtherNetIPModuleAdapter(
        FakeCodesysProvider(
            observation(
                connected=False,
                faulted=True,
                diagnostic_available=True,
                diagnostic_text="remote adapter not found",
            )
        )
    )

    status = adapter.status()

    assert status.diagnostic_code == (
        "codesys-enip:not-running:not-found"
    )
    assert status.diagnostic_message == "remote adapter not found"


def test_reconfigure_request_is_blocked_when_capability_is_absent():
    provider = FakeCodesysProvider(observation(can_reconfigure=False))
    adapter = CodesysEtherNetIPModuleAdapter(provider)

    with pytest.raises(
        CodesysModuleAdapterError,
        match="does not report DED.CanReconfigure",
    ) as caught:
        adapter.request_enabled(False)

    assert caught.value.code == "reconfigure-unsupported"
    assert provider.requests == []


def test_supported_reconfigure_request_delegates_and_returns_correlation_id():
    provider = FakeCodesysProvider(observation(can_reconfigure=True))
    adapter = CodesysEtherNetIPModuleAdapter(provider)

    correlation_id = adapter.request_enabled(False)

    assert correlation_id == "reconfigure-1"
    assert provider.requests == [False]


def test_diagnostic_text_cannot_exist_without_availability():
    with pytest.raises(
        ValueError,
        match="diagnostic_text requires diagnostic_available",
    ):
        observation(diagnostic_text="unavailable")
