from __future__ import annotations

import contextlib
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Asset:
    """Something a team can own."""

    def __init__(
        self,
        name: str,
        _id: str | None = None,
        value: int | None = None,
        team_name: str | None = None,
        pos: str | None = None,
    ):
        self._id = _id
        self.name = name
        self.value = value if value else 0
        self.pos = pos
        self.slots: list[str] = self.pos

        with contextlib.suppress(AttributeError):
            self.team_name = team_name.strip()

    def __eq__(self, val: Asset | str) -> bool:
        if isinstance(val, Asset):
            comp_name = val.name
            comp_id = val._id
        else:
            comp_name = val
            comp_id = None
        return comp_name == self.name or (comp_id is not None and comp_id == self._id)

    def __repr__(self) -> str:
        return f"{self.name} - {self.value:.2f}"


class Team:
    """Collection of players with lineup methods."""

    def __init__(
        self,
        name: str,
        assets: list[Asset],
        lineup_setter: Callable,
    ):
        self.assets = [a for a in assets if a.value is not None]
        self.assets = assets
        self.name = name
        self.set_lineup = partial(lineup_setter, assets=assets)
        self.lineup = None

    def __repr__(self) -> str:
        return f"Team: {self.name}"
