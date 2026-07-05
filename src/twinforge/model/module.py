from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional

from .asset import Asset
from .connection import Connection
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
    slot: int

    catalog: str

    identity: Identity

    parent: Optional["Chassis"] = None

    io: Dict = field(default_factory=dict)

    connections: list["Connection"] = field(default_factory=list)

    # channels: list["Channel"] = field(default_factory=list)

    # assemblies: list["Assembly"] = field(default_factory=list)

    def add_connection(self, connection: "Connection") -> None:
        connection.parent = self
        self.connections.append(connection)

    # def add_channel(self, channel: "Channel") -> None:
    # channel.parent = self
    # self.channels.append(channel)

    # def add_assembly(self, assembly: "Assembly") -> None:
    # assembly.parent = self
    # self.assemblies.append(assembly)
