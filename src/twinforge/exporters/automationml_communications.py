"""Generate vendor-neutral AutomationML communication bindings."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Sequence

from twinforge.model import (
    Controller,
    GatewayDevice,
    GatewayTagBinding,
    GatewayTagBindingRole,
)

from .automationml_elements import (
    attribute,
    external_interface,
    interface_attribute,
    internal_element,
    q,
    role_requirement,
)
from .automationml_types import (
    BASE_DIRECTION_TYPE_PATH,
    TWINFORGE_INTERFACE_LIBRARY,
    TWINFORGE_SYSTEM_UNIT_LIBRARY,
)


def append_gateway_communications(
    system: ET.Element,
    plc: ET.Element,
    controller: Controller,
    gateways: Sequence[GatewayDevice],
    *,
    project_name: str,
) -> None:
    """Append gateways and links for bindings owned by ``controller``."""

    controller_tags = {id(tag) for tag in controller.tags.values()}
    for gateway in gateways:
        gateway_path = f"system/{project_name}/gateway/{gateway.name}"
        gateway_element = internal_element(
            system,
            gateway.name,
            gateway_path,
            system_unit_path=(
                f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/CommunicationGateway"
            ),
        )
        attribute(gateway_element, "AssetType", "CommunicationGateway")
        attribute(gateway_element, "Manufacturer", gateway.manufacturer)
        attribute(
            gateway_element,
            "CatalogNumber",
            gateway.catalog_number or gateway.model,
        )
        for index, binding in enumerate(gateway.tag_bindings):
            if id(binding.tag) not in controller_tags:
                raise ValueError(
                    f"gateway binding {binding.tag_path!r} does not belong "
                    f"to controller {controller.name!r}"
                )
            _append_tag_binding(
                plc,
                gateway_element,
                binding,
                gateway_path=gateway_path,
                controller_path=(
                    f"system/{project_name}/controller/{controller.name}"
                ),
                index=index,
            )
        role_requirement(gateway_element, "CommunicationGateway")


def _append_tag_binding(
    plc: ET.Element,
    gateway: ET.Element,
    binding: GatewayTagBinding,
    *,
    gateway_path: str,
    controller_path: str,
    index: int,
) -> None:
    interface_class = (
        f"{TWINFORGE_INTERFACE_LIBRARY}/CommunicationPointInterface"
    )
    identity_suffix = f"{index}/{binding.tag_path}"
    gateway_interface = external_interface(
        gateway,
        f"{binding.interface_name}:{binding.endpoint_reference}",
        f"{gateway_path}/binding/{identity_suffix}",
        class_path=interface_class,
    )
    controller_interface = external_interface(
        plc,
        binding.tag_path,
        f"{controller_path}/communication-binding/{identity_suffix}",
        class_path=interface_class,
    )
    gateway_direction, controller_direction = _directions(binding.role)
    for element, direction in (
        (gateway_interface, gateway_direction),
        (controller_interface, controller_direction),
    ):
        interface_attribute(
            element,
            "Direction",
            direction,
            "xs:string",
            BASE_DIRECTION_TYPE_PATH,
        )
        attribute(element, "Protocol", binding.interface_name)
        attribute(
            element,
            "EndpointReference",
            binding.endpoint_reference,
        )
        attribute(element, "TagPath", binding.tag_path)
        attribute(element, "BindingEvidence", binding.evidence)
    ET.SubElement(
        plc,
        q("InternalLink"),
        {
            "Name": f"{binding.tag_path}_to_{binding.endpoint_reference}",
            "RefPartnerSideA": controller_interface.attrib["ID"],
            "RefPartnerSideB": gateway_interface.attrib["ID"],
        },
    )


def _directions(role: GatewayTagBindingRole) -> tuple[str, str]:
    """Return gateway-side and controller-side signal directions."""

    if role is GatewayTagBindingRole.SOURCE:
        return "In", "Out"
    return "Out", "In"
