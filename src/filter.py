from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import Callable, Container, Generator
from itertools import chain
from src.classes import Asset, Package, Pick, Pos, Team
from src.exception import CorrespondError, NoValuesError
from src.utils import get_team_from_assets, get_team_from_pos


class Filter(ABC):
    @abstractmethod
    def __call__(self, package: Package) -> bool:
        pass


class SendFilter(Filter):
    """operates on the send package"""

    def __init__(  # noqa: PLR0913
        self,
        # league: League,
        team: Team,
        # opp_team: Team | tuple[Team],
        assets: tuple[Asset] | None = None,
        not_assets: tuple[Asset] | None = None,
        pos: tuple[str] | None = None,
        not_pos: tuple[str] | None = None,
        min_asset_value: int | None = None,
        *,
        assets_exclusive: bool = False,
    ):
        self.team = team
        self.assets = assets
        self.not_assets = not_assets
        self.assets_exclusive = assets_exclusive
        self.pos = pos
        self.not_pos = not_pos
        self.min_asset_value = min_asset_value

    @property
    def all_team_assets(self) -> list[Asset]:
        return self.team.assets

    def __call__(self, package: Package) -> bool:
        """filter package"""

        # Pos:
        if self.pos:
            raise NotImplementedError

        # Not Assets:
        try:
            if any(asset for asset in self.not_assets if asset in package):
                return False
        except TypeError:
            pass

        # Assets:
        try:
            # check if all or any assets need to be in package
            exclusive_send_assets: Callable[[Generator], bool] = (
                all if self.assets_exclusive else any
            )
            necessary_assets_in_package = exclusive_send_assets(
                player in package for player in self.assets
            )
            if not necessary_assets_in_package:
                return False
        except TypeError:
            pass

        # Min Asset Value:
        try:
            if any(asset.value < self.min_asset_value for asset in package):
                return False
        except TypeError:
            pass  # no min value

        return True


class PackageFilter(Filter):
    """operates on the package level"""

    def __init__(
        self,
        max_assets: int = 2,
        return_contains: tuple[str] | None = None,
        min_val: int | Container[int] | None = None,
        target_pos: tuple[Pos] | None = None,
        *,
        return_contains_exclusive: bool = False,
    ):
        self.max_assets = max_assets
        self.return_contains = return_contains
        self.return_contains_exclusive = return_contains_exclusive
        self.min_val = min_val
        self.target_pos = target_pos

    def get_opp_teams(self, league_assets: Container[Asset]) -> set[str]:
        """filter valdi assets, return their teams; may propogate no value error"""

        target_teams: list[str] = []

        # Filter by Asset:
        with contextlib.suppress(TypeError):
            new_teams: set[str] = get_team_from_assets(
                all_assets=league_assets,
                valid_assets=self.return_contains,
            )
            target_teams.append(new_teams)

        # Filter by Position:
        with contextlib.suppress(TypeError):
            new_teams: set[str] = get_team_from_pos(
                all_assets=league_assets,
                valid_pos=self.target_pos,
            )
            target_teams.append(new_teams)

        if len(target_teams) == 0:
            raise NoValuesError(obj_name="opp teams")

        return set(chain(*target_teams))

    def __call__(self, package: Package) -> bool:
        # If Min Value:
        if self.min_val and not self.validate_pos_values(
            package=package,
            target_pos=self.target_pos,
            min_vals=self.min_val,
        ):
            return False

        # Return Contains:
        with contextlib.suppress(TypeError):
            # check if all or any assets need to be in package
            exclusive_return_contains: Callable[[Generator], bool] = (
                all if self.return_contains_exclusive else any
            )
            necessary_assets_in_package = exclusive_return_contains(
                player in package for player in self.return_contains
            )
            if not necessary_assets_in_package:
                return False

        # Check Max Assets:
        if len(package) > self.max_assets:
            return False

        # Contains POS:
        try:
            target_pos_set = set(self.target_pos)
            target_pos_set.add(None)
            positions_in_assets = package.get_positions()
            if len(target_pos_set.intersection(positions_in_assets)) == 0:
                return False
        except TypeError:
            pass

        return True


class ReceiveFilter(Filter):
    """operates on the recieve package"""

    def __init__(
        self,
        min_asset_value: int | None = None,
        return_does_not_contain: tuple[str] | None = None,
        does_not_contain_pos: tuple[Pos] | None = None,
        *,
        use_picks: bool = True,
    ):
        # try:
        #     # ? why is this necessary; isn't this just the argument
        #     self.target_pos: tuple[Pos] = tuple(Pos[pos] for pos in target_pos)
        # except TypeError:
        #     self.target_pos = None

        self.use_picks = use_picks
        self.return_does_not_contain = return_does_not_contain
        self.does_not_contain_pos = does_not_contain_pos
        self.min_asset_value = min_asset_value

    @staticmethod
    def validate_pos_values(
        package: Package,
        target_pos,
        min_vals: Container[float] | None,
    ) -> bool:
        if len(target_pos) != len(min_vals):
            raise CorrespondError("target_pos", "min_vals")

        asset_values = package.get_composite_values_corr()
        asset_positions = package.get_positions_corr()

        # Return true if any picks are above min val
        if not any(asset_positions) and any(
            val >= min(min_vals) for val in asset_values
        ):
            return True

        # Check any valid by position:
        for pos, value in zip(target_pos, min_vals):
            # find where is pos and good value
            assets_where_pos_values = [
                asset
                for asset in package
                if (
                    asset.composite_value >= value
                    and getattr(asset, "pos", None) == pos
                )
            ]
            if len(assets_where_pos_values) > 0:
                return True

        return False

    def __call__(self, package: Package) -> bool:
        # Invalid Positions:
        try:
            any_invalid_positions = any(
                getattr(player.pos, "name", None) in self.does_not_contain_pos
                for player in package.assets
            )
            if any_invalid_positions:
                return False
        except TypeError:
            pass

        # Return Does Not Contain:
        with contextlib.suppress(TypeError):
            any_invalid_players = any(
                player in package for player in self.return_does_not_contain
            )
            if any_invalid_players:
                return False

        # Min Asset Value:
        try:
            if any(asset.value < self.min_asset_value for asset in package):
                return False
        except TypeError:
            pass  # no min value

        # Check if picks are allowed:
        any_picks = any(isinstance(asset, Pick) for asset in package)
        if any_picks and not self.use_picks:
            return False

        return True
