"""Orchestration for bounded, read-only discovery captures."""

from __future__ import annotations

from datetime import datetime, timezone

from .contracts import (
    CipIdentityObservation,
    DiscoveryDiagnostic,
    DiscoveryDiagnosticSeverity,
    DiscoveryOperation,
    DiscoveryProviderError,
    DiscoveryScope,
    DiscoverySnapshot,
    CipDiscoveryProvider,
    SnmpDiscoveryProvider,
    SnmpNodeObservation,
)


def capture_snapshot(
    scope: DiscoveryScope,
    provider: CipDiscoveryProvider,
    *,
    snmp_provider: SnmpDiscoveryProvider | None = None,
    captured_at: datetime | None = None,
) -> DiscoverySnapshot:
    """Capture permitted evidence from every target in deterministic order."""
    timestamp = captured_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("captured_at must include a timezone")

    identities: list[CipIdentityObservation] = []
    snmp_nodes: list[SnmpNodeObservation] = []
    diagnostics: list[DiscoveryDiagnostic] = []
    targets = tuple(sorted(scope.targets, key=lambda target: target.key))

    if DiscoveryOperation.CIP_IDENTITY in scope.operations:
        for target in targets:
            try:
                identities.append(
                    provider.read_cip_identity(
                        target,
                        captured_at=timestamp,
                    )
                )
            except DiscoveryProviderError as error:
                diagnostics.append(
                    DiscoveryDiagnostic(
                        target=target,
                        severity=DiscoveryDiagnosticSeverity.ERROR,
                        code=error.code,
                        message=str(error),
                    )
                )

    if DiscoveryOperation.SNMP_NETWORK in scope.operations:
        if snmp_provider is None:
            for target in targets:
                diagnostics.append(
                    DiscoveryDiagnostic(
                        target=target,
                        severity=DiscoveryDiagnosticSeverity.ERROR,
                        code="snmp_provider_missing",
                        message=(
                            "SNMP network discovery was requested without a provider"
                        ),
                    )
                )
        else:
            for target in targets:
                try:
                    snmp_nodes.append(
                        snmp_provider.read_snmp_node(
                            target,
                            captured_at=timestamp,
                        )
                    )
                except DiscoveryProviderError as error:
                    diagnostics.append(
                        DiscoveryDiagnostic(
                            target=target,
                            severity=DiscoveryDiagnosticSeverity.ERROR,
                            code=error.code,
                            message=str(error),
                        )
                    )

    return DiscoverySnapshot(
        schema_version="1.0",
        engagement=scope.engagement,
        authorization_reference=scope.authorization_reference,
        captured_at=timestamp,
        operations=tuple(sorted(scope.operations, key=lambda item: item.value)),
        targets=targets,
        identities=tuple(sorted(identities, key=lambda item: item.target.key)),
        snmp_nodes=tuple(sorted(snmp_nodes, key=lambda item: item.target.key)),
        diagnostics=tuple(
            sorted(
                diagnostics,
                key=lambda item: (item.target.key, item.code, item.message),
            )
        ),
    )
