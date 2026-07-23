from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

from .asset import Asset
from .connection import Connection
from .electronic_key import ElectronicKey
from .engineering_unit import EngineeringUnitEvidence
from .identity import Identity

if TYPE_CHECKING:
    from .chassis import Chassis

# TODO:
# Introduce Channel and Assembly classes once the
# CIP Assembly Object decoder has been implemented.
#
# At present, raw IO information is stored in `io`.


@dataclass(kw_only=True)
class Module(Asset):
    catalog: str

    identity: Identity

    slot: int | None = None

    address: str | None = None

    electronic_key: ElectronicKey | None = None

    inhibited: bool | None = None

    major_fault_on_connection_loss: bool | None = None

    parent: "Chassis | Module | None" = None

    io: Dict = field(default_factory=dict)

    connections: list["Connection"] = field(default_factory=list)

    child_modules: list["Module"] = field(default_factory=list)

    engineering_units: dict[str, EngineeringUnitEvidence] = field(
        default_factory=dict
    )

    # channels: list["Channel"] = field(default_factory=list)

    # assemblies: list["Assembly"] = field(default_factory=list)

    def add_connection(self, connection: "Connection") -> None:
        connection.parent = self
        self.connections.append(connection)

    def add_child_module(self, module: "Module") -> None:
        module.parent = self
        self.child_modules.append(module)

    # def add_channel(self, channel: "Channel") -> None:
    # channel.parent = self
    # self.channels.append(channel)

    # def add_assembly(self, assembly: "Assembly") -> None:
    # assembly.parent = self
    # self.assemblies.append(assembly)
