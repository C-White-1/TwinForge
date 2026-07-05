from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from .controller import Controller
from .routine import Routine
from .tag import Tag


@dataclass
class Program:
    name: str

    routines: dict[str, Routine] = field(default_factory=dict)

    tags: dict[str, Tag] = field(default_factory=dict)

    parent: Controller | None = None

    main_routine: Routine | None = None

    # -------------------------
    # Construction / Mutation
    # -------------------------

    def set_main_routine(self, routine: Routine) -> None:
        if routine.name not in self.routines:
            raise ValueError("Routine must belong to this program.")

        self.main_routine = routine

    def add_routine(self, routine: Routine) -> None:
        if routine.name in self.routines:
            raise ValueError(f"Routine '{routine.name}' already exists")

        routine.parent = self
        self.routines[routine.name] = routine

        if self.main_routine is None:
            self.set_main_routine(routine)

    def add_tag(self, tag: Tag) -> None:
        if tag.name in self.tags:
            raise ValueError(f"Tag '{tag.name}' already exists")

        tag.parent = self
        self.tags[tag.name] = tag

    # -------------------------
    # Lookup
    # -------------------------

    def get_routine(self, name: str) -> Routine | None:
        return self.routines.get(name)

    def get_tag(self, name: str) -> Tag | None:
        return self.tags.get(name)

    # -------------------------
    # Iteration
    # -------------------------

    def iter_routines(self) -> Iterator[Routine]:
        yield from self.routines.values()

    def iter_tags(self) -> Iterator[Tag]:
        yield from self.tags.values()
