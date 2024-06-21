from __future__ import annotations

from itertools import chain
from typing import (
    Callable,
    NewType,
)

from src._enum import Pos, Role

DynastyValue = NewType("DynastyValue", float)  # TODO: I don't like this
StarterValue = NewType("StarterValue", float)


class Asset:
    """Something a team can own"""

    def __init__(  # noqa: PLR0913
        self,
        _id: str,
        name: str,
        dynasty_value: int,
        starter_value: int | None = None,
        team_name: str | None = None,
        pos: Pos | None = None,
        value_fn: Callable[[DynastyValue, StarterValue], float] | None = None,
    ):
        self._id = _id
        self.name = name
        self.starter_value = starter_value
        self.dynasty_value = dynasty_value
        self.pos = pos
        if pos:
            self.pos = Pos[pos]
            self.roles = self.pos.value
            self.slots = set(chain.from_iterable([slots.value for slots in self.roles]))
        self.team_name = team_name
        try:
            self.value = value_fn(self.dynasty_value, self.starter_value)
        except TypeError:
            self.value = None


class Player(Asset):
    """A league member"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slots: list[str] = self.pos

    def __eq__(self, val: str) -> bool:
        return val in (self.name, self._id)

    def __hash__(self):
        return hash((self.name, self._id))

    def __repr__(self) -> str:
        return f"{self.name}, {self.pos.name}, Value: {self.value}>"


class Pick(Asset):
    """An owned draft pick"""

    @staticmethod
    def pick_as_name(pick_number: int) -> str:
        """create the asset name from pick"""
        return f"pick--{pick_number}"

    def __init__(self, pick_number: int, **kwargs):
        super().__init__(**kwargs, name=self.pick_as_name(pick_number))
        self.pick_number = pick_number
        self.roles = tuple(Role)

    def __eq__(self, val: str) -> bool:
        return val in (self.name, self._id)

    def __hash__(self):
        return hash((self.name, self._id))

    def __repr__(self) -> str:
        return f"{self.name}, Value: {self.value}>"
