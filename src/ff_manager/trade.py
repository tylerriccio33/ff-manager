from collections.abc import Callable, Generator
from copy import copy

from ff_manager.model import Asset, Team
from ff_manager.utils import diff_assets


class Package:
    def __init__(self, assets: set[Asset]):
        self.assets = assets
        self._positions = {getattr(asset, "pos", None) for asset in self.assets}

    def _get_composite_values(self) -> Generator:
        return (asset.composite_value for asset in self.assets)

    def get_composite_values_corr(self) -> list:
        return list(self._get_composite_values())

    def __iter__(self):
        return iter(self.assets)

    def __len__(self) -> int:
        return len(self.assets)


class Trade:
    """object holding details of a trade."""

    def __init__(
        self,
        team1: Team,
        team2: Team,
        package1: Package,
        package2: Package,
        lineup_setter: Callable,
    ):
        self._lineup_setter = lineup_setter
        self.team1 = copy(team1)
        self.team2 = copy(team2)
        self.package1 = package1
        self.package2 = package2
        self.sent_assets = package1.assets
        self.rec_assets = package2.assets
        self.value1: float | None = None
        self.value2: float | None = None

    def execute_trade(self) -> None:
        """Execute the trade."""
        # Create new team1:
        retained_assets = diff_assets(assets=self.team1.assets, rm=self.sent_assets)
        new_team1_assets = tuple(retained_assets + self.rec_assets)
        self.new_team1 = Team(
            name=self.team1.name,
            assets=new_team1_assets,
            lineup_setter=self._lineup_setter,
        )
        self.new_team1.lineup = self.new_team1.set_lineup()
        self.new_team1_value = self.new_team1.lineup.total_value

        # Create new team2:
        retained_assets = diff_assets(assets=self.team2.assets, rm=self.rec_assets)
        new_team2_assets = tuple(retained_assets + self.sent_assets)
        self.new_team2 = Team(
            name=self.team2.name,
            assets=new_team2_assets,
            lineup_setter=self._lineup_setter,
        )
        self.new_team2.lineup = self.new_team2.set_lineup()
        self.new_team2_value = self.new_team2.lineup.total_value

        # Get Difference in Values:
        self.team1.lineup = self.team1.set_lineup()
        self.team2.lineup = self.team2.set_lineup()
        self.team1_gain = self.new_team1_value - self.team1.lineup.total_value
        self.team2_gain = self.new_team2_value - self.team2.lineup.total_value

    def __repr__(self):
        return f"""
              == Trade ================================================================
              Team1: {self.team1.name}
              Team2: {self.team2.name}
              Assets Sent: {self.sent_assets}
              Assets Received: {self.rec_assets}
              Team1 Lineup:
              {self.new_team1.lineup.pprint()}
              Team2 Lineup:
              {self.new_team2.lineup}
              Team1 Gain: {self.team1_gain:.2f}
              Team2 Gain: {self.team2_gain:.2f}
              Team1 Value: {self.new_team1_value:.2f}
              Team2 Value: {self.new_team2_value:.2f}
              """
