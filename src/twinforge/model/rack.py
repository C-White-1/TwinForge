from dataclasses import dataclass, field

from .module import Module


@dataclass
class Rack:
    number: int

    modules: dict[int, Module] = field(default_factory=dict)

    network: str | None = None
