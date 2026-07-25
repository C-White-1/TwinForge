"""Aggregate root for a complete TwinForge plant model."""

from __future__ import annotations

from dataclasses import dataclass, field

from .controller import Controller
from .plant import Plant


@dataclass
class Twin:
    """A plant model with digital-twin-level metadata."""

    plant: Plant
    metadata: dict[str, object] = field(default_factory=dict)

    def add_controller(self, controller: Controller) -> None:
        """Attach a controller to the underlying plant."""

        self.plant.controllers.append(controller)

    def controllers(self) -> list[Controller]:
        """Return the controllers currently attached to the plant."""

        return self.plant.controllers
