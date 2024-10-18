from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ff_manager.utils import containerize_str

if TYPE_CHECKING:
    from collections.abc import Callable, Container, Generator

    from ff_manager.league import Asset
    from ff_manager.trade import Package


class Filter(ABC):
    @abstractmethod
    def __call__(self, package: Package) -> bool:
        pass


class SendFilter(Filter):
    """
    Filter operating on the send package.

    assets (tuple[str] | None): Assets to send.
    not_assets (tuple[str] | None): Assets that cannot be sent.
    pos (tuple[str] | None): Positions to send.
    not_pos (tuple[str] | None): Positions that cannot be sent.
    min_asset_value (int | None): Minimum asset value that can be sent.
    assets_exclusive (bool): Whether to only send those particular assets.
    """

    def __init__(
        self,
        assets: tuple[str] | None = None,
        not_assets: tuple[str] | None = None,
        pos: tuple[str] | None = None,
        not_pos: tuple[str] | None = None,
        min_asset_value: int | None = None,
        *,
        assets_exclusive: bool = False,
        **kwargs,
    ):
        self.assets = containerize_str(assets)
        self.not_assets = containerize_str(not_assets)
        self.assets_exclusive = assets_exclusive
        self.pos = containerize_str(pos)
        self.not_pos = containerize_str(not_pos)
        self.min_asset_value = min_asset_value

    def __call__(self, package: Package) -> bool:
        """Filter package."""
        # Pos:
        with contextlib.suppress(TypeError):
            for pos in self.pos:
                any_valid_pos = any(pos in player.slots for player in package.assets)
                if any_valid_pos:
                    break
            else:
                return False

        # Not Assets:
        with contextlib.suppress(TypeError):
            if any(asset for asset in self.not_assets if asset in package):
                return False

        # Assets:
        with contextlib.suppress(TypeError):
            # check if all or any assets need to be in package
            exclusive_send_assets: Callable[[Generator], bool] = (
                all if self.assets_exclusive else any
            )
            necessary_assets_in_package = exclusive_send_assets(
                player in package for player in self.assets
            )
            if not necessary_assets_in_package:
                return False

        # Min Asset Value:
        with contextlib.suppress(TypeError):
            if any(asset.value < self.min_asset_value for asset in package):
                return False

        return True


class PackageFilter(Filter):
    """
    Filter at the package level.

    max_assets (int, optional): _description_. Defaults to 2.
    return_contains (tuple[str] | None, optional): _description_.
    assets_from_team (str | None, optional): Team to draw potential recieve assets from.
    target_pos (tuple[Pos] | None, optional): Positions to be included.
    return_contains_exclusive (bool, optional): _description_. Defaults to False.
    """

    def __init__(
        self,
        max_assets: int = 2,
        return_contains: tuple[str] | None = None,
        assets_from_team: str | None | tuple[str] = None,
        assets_not_from_team: str | tuple[str] | None = None,
        target_pos: tuple | None = None,
        not_receive_pos: tuple | None = None,
        *,
        return_contains_exclusive: bool = False,
        **kwargs,
    ):
        self.max_assets = max_assets
        self.return_contains = return_contains
        self.assets_from_team = containerize_str(
            assets_from_team
        )  # TODO: validate this; make set?
        self.assets_not_from_team = containerize_str(assets_not_from_team)
        self.not_receive_pos = containerize_str(not_receive_pos)
        self.target_pos = containerize_str(target_pos)

        if self.return_contains and self.target_pos:
            raise ValueError(
                "Only one of `return_contains` and `target_pos` can be passed."
            )

        self.return_contains_exclusive = return_contains_exclusive

    def get_matching_teams(self, league_assets: Container[Asset]) -> set[str]:
        """Find all (including own) teams matching the criteria."""
        if self.assets_from_team:
            return set(self.assets_from_team)

        # Teams owning a desired asset
        with contextlib.suppress(TypeError):
            return {
                asset.team_name
                for asset in league_assets
                if asset in self.return_contains
            }

        all_teams = {asset.team_name for asset in league_assets}  # default

        if self.assets_not_from_team:
            for team in self.assets_not_from_team:
                all_teams.discard(team)

        return all_teams

    def __call__(self, package: Package) -> bool:
        # Return contains:
        with contextlib.suppress(TypeError):  # if no return contains
            # check if all or any assets need to be in package
            exclusive_return_contains: Callable[[Generator], bool] = (
                all if self.return_contains_exclusive else any
            )
            necessary_assets_in_package = exclusive_return_contains(
                player in package for player in self.return_contains
            )
            if not necessary_assets_in_package:
                return False

        # Contains POS:
        with contextlib.suppress(TypeError):
            target_pos_set: set[str] = set(self.target_pos) | {None}
            overlapping_positions = target_pos_set & package._positions
            if not overlapping_positions:
                return False

        # Not contains Pos:
        with contextlib.suppress(TypeError):
            if set(self.not_receive_pos) & package._positions:
                return False

        return True


class ReceiveFilter(Filter):
    """operates on the recieve package."""

    def __init__(
        self,
        min_asset_value: int | None = None,
        return_does_not_contain: tuple[str] | None = None,
        return_not_pos: tuple | None = None,
        **kwargs,
    ):
        self.return_does_not_contain = return_does_not_contain
        self.return_not_pos = containerize_str(return_not_pos)
        self.min_asset_value = min_asset_value

    def __call__(self, package: Package) -> bool:
        # Invalid Positions:
        with contextlib.suppress(TypeError):
            any_invalid_positions = any(
                player for player in package if player.pos in self.return_not_pos
            )
            if any_invalid_positions:
                return False

        # Return Does Not Contain:
        with contextlib.suppress(TypeError):
            any_invalid_players = any(
                player in package for player in self.return_does_not_contain
            )
            if any_invalid_players:
                return False

        # Min Asset Value:
        with contextlib.suppress(TypeError):
            if any(asset.value < self.min_asset_value for asset in package):
                return False

        return True
