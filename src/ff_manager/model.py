from __future__ import annotations

from collections import deque
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Asset:
    """Something a team can own."""

    def __init__(
        self,
        _id: str,
        name: str,
        value: int,
        team_name: str | None = None,
        pos: str | None = None,
    ):
        self._id = _id
        self.name = name
        self.value = value
        self.pos = pos
        self.slots: list[str] = self.pos
        self.team_name = team_name.strip()

    def __eq__(self, val: str) -> bool:
        return val in (self.name, self._id)

    def __repr__(self) -> str:
        return f"{self.name}, {self.pos}, Value: {self.value:.2f}>"


class Team:
    """Collection of players with lineup methods."""

    def sort_assets(self) -> deque[Asset]:
        return deque(sorted(self.assets, key=lambda x: x.value, reverse=True))

    def __init__(
        self,
        name: str,
        assets: list[Asset],
        lineup_setter: Callable,
    ):
        self.assets = [a for a in assets if a.value is not None]
        self.sorted_assets = self.sort_assets()
        self.name = name
        self.set_lineup = partial(lineup_setter, sorted_assets=self.sorted_assets)
        self.lineup = None

    def calc_extended_lineup_value(
        self,
        decay: float | None = None,
        include_window: int = 2,
    ) -> float:
        """Calculate value for lineup plus lineup adjacent spots."""
        lineup_assets: Asset = tuple(self.lineup.values())
        lineup_value: int = sum(
            asset.value for asset in lineup_assets if asset is not None
        )

        all_proximal_assets = [
            asset for asset in self.assets if asset not in lineup_assets
        ]
        sorted_proximal_assets = sorted(
            all_proximal_assets,
            key=lambda x: x.value,
            reverse=True,
        )

        """
        Weighting Position:
            Position is weighted by ability of the player to "fill in".
            For example, qbs can only fill in super and qb.
            On the contrary, wrs can fill in wr, flex and super.
            This makes a wr more valueable since it's more likely to enter the lineup.
        """
        pct_slots_fillable: list[float] = []
        for asset in sorted_proximal_assets:
            asset_pct_slots_fillable = self.lineup.pos_slots_fillable(asset.pos)
            pct_slots_fillable.append(asset_pct_slots_fillable)

        # Don't assign to asset, since it's an object
        new_asset_value = [
            asset.value * pct_fillable
            for asset, pct_fillable in zip(
                sorted_proximal_assets, pct_slots_fillable, strict=False
            )
        ]
        new_asset_value_sorted_i = sorted(
            range(len(new_asset_value)),
            key=new_asset_value.__getitem__,
            reverse=True,
        )  # this is the same as np.argsort

        sorted_proximal_assets = [
            sorted_proximal_assets[i] for i in new_asset_value_sorted_i
        ]

        """
        Weighting Distance From Lineup:
            Distance weighted by a decay, which values the player closer to the lineup.
            This is intuitive since the closer player is more likely to enter.
        """
        if decay is not None:
            raise NotImplementedError("Weight decay passed but not implemented.")

        # Slice:
        sliced_proximal_assets = sorted_proximal_assets[:include_window]
        sliced_proximal_assets_value: int = sum(
            asset.value for asset in sliced_proximal_assets
        )
        self.sorted_proximal_assets = sorted_proximal_assets  # ! I know this is bad

        return lineup_value + sliced_proximal_assets_value

    def __repr__(self) -> str:
        return f"Team: {self.name}"

    def pprint_sorted_proximal_assets(self) -> str:
        return "\n\t\t\t\t\t\t\t\t\t".join(
            str(asset) for asset in self.sorted_proximal_assets[:2]
        )
