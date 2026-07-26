"""Evidence-driven assembly of devices from controller representations."""

from __future__ import annotations

from copy import deepcopy

from twinforge.model import (
    CommunicationInterface,
    Device,
    DeviceModuleBinding,
    DeviceModuleRole,
    DeviceType,
    Identity,
    Module,
)


def assemble_device_from_module(
    module: Module,
    *,
    name: str,
    device_type: DeviceType,
    evidence: str,
    manufacturer: str | None = None,
    model: str | None = None,
    catalog_number: str | None = None,
    identity: Identity | None = None,
    binding_role: DeviceModuleRole = DeviceModuleRole.CYCLIC_IO,
    interface_name: str | None = None,
) -> Device:
    """Create a device only when its physical identity is explicit.

    The function deliberately does not infer an asset from the module catalog
    or vendor fields. A source adapter or caller must provide the evidence
    that the controller representation belongs to the named device.
    """

    if not name.strip():
        raise ValueError("device name must be explicit")
    if not evidence.strip():
        raise ValueError("device-module binding evidence must be explicit")

    device = Device(
        name=name,
        device_type=device_type,
        manufacturer=manufacturer,
        model=model,
        catalog_number=catalog_number,
        identity=identity,
    )
    device.bind_module(
        DeviceModuleBinding(
            module=module,
            role=binding_role,
            evidence=evidence,
            metadata={
                "module_identity_scope": "controller_representation",
                "device_identity_scope": "represented_device",
            },
            source_extensions=list(module.source_extensions),
        )
    )

    protocols = {
        connection.protocol
        for connection in module.connections
        if connection.protocol
    }
    if protocols:
        for protocol in sorted(protocols):
            interface = CommunicationInterface(
                name=interface_name or protocol,
                protocol=protocol,
                address=module.address,
            )
            for connection in module.connections:
                if connection.protocol == protocol:
                    interface.add_connection(deepcopy(connection))
            device.add_communication_interface(interface)

    return device
