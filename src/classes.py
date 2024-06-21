"""Classes for main; ordered by level of abstraction"""

from __future__ import annotations

from collections import deque
from copy import copy
from typing import (
    Callable,
    Generator,
)

from src._enum import LineupSlots, Pos, Role
from src.asset import Asset, DynastyValue, Pick, Player, StarterValue
from src.utils import _correct_fuzzy_team_names

# TODO: Implement better inheretence pattern from assets
# - each asset should have a name and id
# - id can be randomly generated?
# - name can be a concat one if pick


"""
Notes on Linups, Slots and Positions:
    Positions `Pos` consist of QB, RB, WR and TE; the position that's literally played.
    A position `Pos` returns a tuple of valid roles.
    Roles represent the type of roles you'll see in a lineup.
    For example, a `flex` is a role while `flex1` is a slot.
    Roles return a tuple of slots.
    A slot specifically, is a location on a lineup.
    As mentioned, `RB1` or `SUPER1` is a slot.
"""


class Team:
    """Collection of players with lineup methods"""

    def sort_assets(self) -> deque[Asset]:
        return deque(sorted(self.assets, key=lambda x: x.value, reverse=True))

    def __init__(
        self,
        name: str,
        assets: list[Asset],
    ):
        self.assets = assets
        self.sorted_assets = self.sort_assets()
        self.name = name
        self.lineup = None

    def _set_asset_set(self) -> None:
        self._asset_set = set(self.assets)

    def calc_lineup_value(self) -> float:
        return sum(player.value for player in self.lineup.values())

    def calc_extended_lineup_value(
        self,
        decay: float | None = None,
        include_window: int = 4,
    ) -> float:
        """calculate value for lineup plus lineup adjacent spots"""
        lineup_assets: Asset = tuple(self.lineup.values())
        lineup_value: int = sum(asset.value for asset in lineup_assets)

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
        lineup_len = LineupSlots.__len__()
        pct_slots_fillable: list[float] = []
        for asset in sorted_proximal_assets:
            if isinstance(asset, Pick):
                pct_slots_fillable.append(1)
            else:
                slots_fillable: list[LineupSlots] = Pos.get_available_slots(asset.pos)
                asset_pct_slots_fillable = len(slots_fillable) / lineup_len
                pct_slots_fillable.append(asset_pct_slots_fillable)

        # Don't assign to asset, since it's an object
        new_asset_value = [
            asset.value * pct_fillable
            for asset, pct_fillable in zip(sorted_proximal_assets, pct_slots_fillable)
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

    def __iter__(self):
        return iter(self.assets)

    def __contains__(self, val) -> bool:
        return any(val == a for a in self.assets)

    def __repr__(self) -> str:
        return f"Team: {self.name}"

    def pprint_sorted_proximal_assets(self) -> str:
        return "\n\t\t\t\t\t\t\t\t\t".join(
            str(asset) for asset in self.sorted_proximal_assets[:4]
        )

    # @profile
    def set_lineup(
        self,
        *,
        include_picks=True,  # noqa: ARG002
    ) -> None:
        """Organize assets to fit most value into lineup"""

        # TODO: implement pick inclusion

        cur_assets = self.sorted_assets.copy()

        lineup = LineupSlots.build_lineup_from_slots()

        for role, slot in Role.unpack_roles():
            eligable_assets = next((a for a in cur_assets if role in a.roles), None)

            if eligable_assets:
                # sel top asset
                top_asset = eligable_assets
                # set lineup
                lineup[slot.name] = top_asset
                # rm asset
                cur_assets.remove(top_asset)

        self.lineup = lineup


class League:
    """The league encapsulates everything; much of the orchestration is done here"""

    def _make_players_from_data(self) -> list[Player]:
        """Instantiate players for each raw player returned from api"""
        return [
            Player(
                _id=i["id"],
                team_name=i["team"],
                name=i["name"],
                pos=i["pos"],
                dynasty_value=i["dynasty_value"],
                starter_value=i["starter_value"],
                value_fn=self.value_fn,
            )
            for i in self.raw_player_data
        ]

    def _make_picks_from_data(self) -> list[Pick]:
        """Instantiate picks for each raw pick returned from api"""
        return [
            Pick(
                _id=i["id"],
                team_name=i["team"],
                dynasty_value=i["dynasty_value"],
                pick_number=i["pick_number"],
                value_fn=self.value_fn,
            )
            for i in self.raw_pick_data
        ]

    def _build_teams(self) -> list[Team]:
        """Take all assets and build list of teams"""
        team_names: set[str] = {p.team_name for p in self.players}

        teams: list[Team] = []
        for team in team_names:
            cur_players = tuple(p for p in self.players if p.team_name == team)
            cur_picks = tuple(p for p in self.picks if p.team_name == team)
            # TODO: allow players and picks to be passed separately
            cur_team = Team(assets=list(cur_players + cur_picks), name=team)
            cur_team.set_lineup()
            teams.append(cur_team)
        return teams

    def __init__(
        self,
        raw_player_data: dict,
        raw_pick_data: dict,
        value_fn: Callable[[DynastyValue, StarterValue], float],
    ):
        self.raw_player_data = raw_player_data
        self.raw_pick_data = raw_pick_data
        self.value_fn = value_fn
        self.players: list[Player] = self._make_players_from_data()
        self.picks: list[Pick] = self._make_picks_from_data()
        self.teams: list[Team] = self._build_teams()

    @property
    def assets(self) -> list[Asset]:
        return self.players + self.picks
    
    def __iter__(self):
        """Iterate over team names"""
        names = [team.name for team in self.teams]
        return iter(names)

    def __getitem__(self, index):
        """get team by team name or index of team"""
        if isinstance(index, int):
            return self.teams[index]
        elif isinstance(index, str):
            names = [team.name for team in self.teams]
            try:
                i = names.index(index)
            except ValueError:
                # TODO: clean this interface
                try:
                    name_map = _correct_fuzzy_team_names(
                        invalid_names=[index],
                        valid_names=names,
                    )
                    i = names.index(name_map[index])
                except ValueError as ve:
                    raise NotImplementedError from ve
            return self.teams[i]
        else:
            raise TypeError("Index must be an integer or a string")  # noqa: TRY003


class Package:
    def __init__(self, assets: set[Asset]):
        self.assets = assets

    def _get_positions(self) -> Generator:
        return (getattr(asset, "pos", None) for asset in self.assets)

    def get_positions(self) -> set:
        return set(self._get_positions())

    def get_positions_corr(self) -> list:
        return list(self._get_positions())

    def _get_dynasty_values(self) -> Generator:
        return (asset.dynasty_value for asset in self.assets)

    def get_dynasty_values_corr(self) -> list:
        return list(self._get_dynasty_values())

    def _get_composite_values(self) -> Generator:
        return (asset.composite_value for asset in self.assets)

    def get_composite_values_corr(self) -> list:
        return list(self._get_composite_values())

    def __getitem__(self, name: str | int) -> set[Asset]:
        # TODO: Implement a container method
        return {asset for asset in self.assets if asset.name == name}

    def __contains__(self, val) -> bool:
        return val in self.assets

    def __iter__(self):
        return iter(self.assets)

    def __len__(self) -> int:
        return len(self.assets)

    def __repr__(self) -> str:
        return "\n\t\t\t\t\t\t\t\t\t".join(str(asset) for asset in self.assets)


class Trade:
    """object holding details of a trade"""

    @staticmethod
    def _rm_assets(assets: list[Asset], rm: list[Asset]) -> tuple:
        valid_assets = assets.copy()
        for asset in rm:
            valid_assets.remove(asset)
        return tuple(valid_assets)

    def __init__(self, team1: Team, team2: Team, package1: Package, package2: Package):
        self.team1 = copy(team1)
        self.team2 = copy(team2)
        self.package1 = package1
        self.package2 = package2
        self.sent_assets = package1.assets
        self.rec_assets = package2.assets
        self.value1: float | None = None
        self.value2: float | None = None

    def execute_trade(self) -> None:
        """implement ftrade, adding new teams"""
        # TODO: add real docstring to this

        # Create new team1:
        valid_assets = self._rm_assets(assets=self.team1.assets, rm=self.sent_assets)
        new_team1_assets = tuple(valid_assets + self.rec_assets)
        self.new_team1 = Team(name=self.team1.name, assets=new_team1_assets)
        self.new_team1.set_lineup()
        self.new_team1_value = self.new_team1.calc_extended_lineup_value()

        # Create new team2:
        valid_assets = self._rm_assets(assets=self.team2.assets, rm=self.rec_assets)
        new_team2_assets = tuple(valid_assets + self.sent_assets)
        self.new_team2 = Team(name=self.team2.name, assets=new_team2_assets)
        self.new_team2.set_lineup()
        self.new_team2_value = self.new_team2.calc_extended_lineup_value()

        # Get Difference in Values:
        self.team1_gain = self.new_team1_value - self.team1.calc_extended_lineup_value()
        self.team2_gain = self.new_team2_value - self.team2.calc_extended_lineup_value()

    def __repr__(self):
        return f"""
              == Trade ================================================================
              Team1: {self.team1.name}
              Team2: {self.team2.name}
              Assets Sent: {self.sent_assets}
              Assets Received: {self.rec_assets}
              Team1 Lineup: {self.new_team1.lineup}
              Team1 Bench: {self.new_team1.pprint_sorted_proximal_assets()}
              Team2 Lineup: {self.new_team2.lineup}
              Team2 Bench: {self.new_team2.pprint_sorted_proximal_assets()}
              Team1 Gain: {round(self.team1_gain, 4)}
              Team2 Gain: {round(self.team2_gain, 4)}
              """
