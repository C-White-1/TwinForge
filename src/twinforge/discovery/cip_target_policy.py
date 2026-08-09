"""Shared network-target policy for live CIP discovery adapters."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network, ip_address

from .contracts import DiscoveryProviderError, DiscoveryTarget


_RFC1918_NETWORKS = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)


def validate_live_cip_target_address(target: DiscoveryTarget) -> None:
    """Require an IPv4 literal in an explicitly permitted local range.

    CIP routes are intentionally allowed here: for routed operations the
    address identifies the directly contacted gateway, while a separate route
    permit controls traversal beyond it.
    """
    try:
        address = ip_address(target.address)
    except ValueError as error:
        raise DiscoveryProviderError(
            "cip_ipv4_literal_required",
            "live CIP discovery requires an IPv4 address literal",
        ) from error
    if not isinstance(address, IPv4Address):
        raise DiscoveryProviderError(
            "cip_ipv4_literal_required",
            "live CIP discovery currently supports IPv4 only",
        )
    if not _is_permitted_local_address(address):
        raise DiscoveryProviderError(
            "cip_public_target_rejected",
            f"public target {target.address} is not permitted by the local-only policy",
        )


def _is_permitted_local_address(address: IPv4Address) -> bool:
    """Recognize RFC 1918, loopback, and IPv4 link-local addresses."""
    return (
        any(address in network for network in _RFC1918_NETWORKS)
        or address.is_loopback
        or address.is_link_local
    )
