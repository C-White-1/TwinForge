from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import List

from .asset import Asset
from .controller import Controller
from .network import Network


@dataclass
class Plant(Asset):
    name: str = ""

    controllers: List[Controller] = field(default_factory=list)

    networks: List[Network] = field(default_factory=list)

    assets: List[Asset] = field(default_factory=list)

    def add_controller(self, controller: Controller) -> None:
        controller.parent = self
        self.controllers.append(controller)

    def add_network(self, network: Network) -> None:
        network.parent = self
        self.networks.append(network)

    def add_asset(self, asset: Asset) -> None:
        asset.parent = self
        self.assets.append(asset)

    # -------------------------
    # Iteration
    # -------------------------

    def iter_controllers(self) -> Iterator[Controller]:
        yield from self.controllers
