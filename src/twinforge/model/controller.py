from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .asset import Asset
from .chassis import Chassis
from .identity import Identity
from .datatype import Datatype

if TYPE_CHECKING:
    from .module import Module
    from .program import Program
    from .tag import Tag
    from .task import Task


@dataclass(kw_only=True)
class Controller(Asset):
    identity: Identity

    name: str = ""

    chassis: dict[str, Chassis] = field(default_factory=dict)

    programs: dict[str, Program] = field(default_factory=dict)

    tasks: dict[str, Task] = field(default_factory=dict)

    tags: dict[str, Tag] = field(default_factory=dict)

    datatypes: dict[str, Datatype] = field(default_factory=dict)

    unplaced_modules: list[Module] = field(default_factory=list)

    parent: object | None = None

    # -------------------------
    # Construction / Mutation
    # -------------------------
    def add_chassis(self, chassis: Chassis) -> None:
        if chassis.name in self.chassis:
            raise ValueError(f"Chassis '{chassis.name}' already exists")

        chassis.parent = self
        self.chassis[chassis.name] = chassis

    def add_program(self, program: Program) -> None:
        if program.name in self.programs:
            raise ValueError(f"Program '{program.name}' already exists")

        program.parent = self
        self.programs[program.name] = program

    def add_task(self, task: Task) -> None:
        if task.name in self.tasks:
            raise ValueError(f"Task '{task.name}' already exists")

        task.parent = self
        self.tasks[task.name] = task

    def add_tag(self, tag: Tag) -> None:
        if tag.name in self.tags:
            raise ValueError(f"Tag '{tag.name}' already exists")

        tag.parent = self
        self.tags[tag.name] = tag

    def add_datatype(self, datatype: Datatype) -> None:
        if datatype.name in self.datatypes:
            raise ValueError(f"Datatype '{datatype.name}' already exists")
        datatype.parent = self
        self.datatypes[datatype.name] = datatype

    def add_unplaced_module(self, module: Module) -> None:
        module.parent = None
        self.unplaced_modules.append(module)

    # -------------------------
    # Lookup
    # -------------------------
    def get_chassis(self, name: str) -> Chassis | None:
        return self.chassis.get(name)

    def get_program(self, name: str) -> Program | None:
        return self.programs.get(name)

    def get_task(self, name: str) -> Task | None:
        return self.tasks.get(name)

    def get_tag(self, name: str) -> Tag | None:
        return self.tags.get(name)

    def get_datatype(self, name: str) -> Datatype | None:
        return self.datatypes.get(name)

    # -------------------------
    # Iteration
    # -------------------------

    def iter_chassis(self) -> Iterator[Chassis]:
        yield from self.chassis.values()

    def iter_programs(self) -> Iterator[Program]:
        yield from self.programs.values()

    def iter_tasks(self) -> Iterator[Task]:
        yield from self.tasks.values()

    def iter_tags(self) -> Iterator[Tag]:
        yield from self.tags.values()

    # -------------------------
    # Representation
    # -------------------------

    def __str__(self) -> str:
        return (
            f"{self.name} "
            f"[{len(self.chassis)} chassis, "
            f"{len(self.programs)} programs, "
            f"{len(self.tasks)} tasks, "
            f"{len(self.tags)} tags]"
        )
