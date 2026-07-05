from dataclasses import dataclass, field
from typing import Optional
from .asset import Asset
from collections.abc import Iterator

from .module import Module


@dataclass
class Chassis(Asset):

    name: str = ""

    modules: dict[int, Module] = field(default_factory=dict)
    
    # -------------------------
    # Construction / Mutation
    # -------------------------
    def add_module(self, module: Module) -> None:
        module.parent = self
        self.modules[module.slot] = module
    
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
