from dataclasses import dataclass, field
from typing import Optional
from .asset import Asset
from collections.abc import Iterator

from .module import Module


@dataclass
class Chassis(Asset):

    name: str = ""

    modules: dict[int, Module] = field(default_factory=dict)

    # A power supply mounts in its own dedicated position, physically
    # separate from the numbered I/O/CPU slot scheme -- not a slotted module.
    power_supplies: list[Module] = field(default_factory=list)

    # -------------------------
    # Construction / Mutation
    # -------------------------
    def add_module(self, module: Module) -> None:
        if module.slot is None:
            raise ValueError(f"Module '{module.name}' does not have a chassis slot")
        if module.slot in self.modules:
            raise ValueError(f"Slot {module.slot} already contains a module")
        module.parent = self
        self.modules[module.slot] = module

    def add_power_supply(self, module: Module) -> None:
        module.parent = self
        self.power_supplies.append(module)

    # -------------------------
    # Lookup
    # -------------------------
    def get_module(self, slot: int) -> Optional[Module]:
        return self.modules.get(slot)
    
    # -------------------------
    # Iteration
    # -------------------------
    def iter_modules(self) -> Iterator[Module]:
        yield from self.modules.values()
    
    # -------------------------
    # Representation
    # -------------------------
    def __str__(self) -> str:
        return f"{self.name} ({len(self.modules)} modules)"
