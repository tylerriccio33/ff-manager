import abc
from difflib import SequenceMatcher as SM
from pathlib import Path
from typing import TypedDict

import click
import polars as pl

from ff_manager.const import KNOWN_PLAYER_MISMATCHES, TEAM_NAME_MATCH_CAP
from ff_manager.lineup import make_lineup_setter
from ff_manager.model import Asset, Team
from ff_manager.utils import hierarchical_data_load


class _PlayerData(TypedDict):
    id: int | str
    team: str
    name: str
    pos: str
    value: float


class BaseLeague(abc.ABC):
    """Base class describing protocols for valid leagues."""

    def __init__(
        self,
        profile: dict,
        *,
        refresh_data: bool = False,
        data_loc: str | Path | None = None,
    ):
        self.profile = profile
        if refresh_data:
            raw_data = self._download_data()
            self.save_data(data=raw_data, outfile_loc=data_loc)
            self.player_data = raw_data
        else:
            self.player_data = hierarchical_data_load(data_loc)

        self.players: list[Asset] = self._make_players_from_data()
        self.lineup_setter = make_lineup_setter(profile)
        self.teams = self._build_teams()

    @abc.abstractmethod
    def _download_data(self) -> list[_PlayerData]:
        """Download and form data from the internet."""

    def save_data(self, data: list[_PlayerData], outfile_loc: str | Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        pa_data = pa.Table.from_pylist(data)
        pq.write_table(pa_data, outfile_loc)

    def __getitem__(self, index):
        """Get team by team name or index of team."""
        if isinstance(index, int):
            return self.teams[index]
        if isinstance(index, str):
            names = [team.name for team in self.teams]
            match_ratios: list[float] = [
                SM(None, index, name).ratio() for name in names
            ]
            valid_i = [
                i
                for i, ratio in enumerate(match_ratios)
                if ratio >= TEAM_NAME_MATCH_CAP
            ]
            if len(valid_i) != 1:
                msg = (
                    "The team name provided was either too broad or matched multiple good options. "
                    f"Please choose from one of the following options --> {names!r}"
                )
                raise ValueError(msg)
            i = valid_i[0]

            return self.teams[i]
        msg = "Index must be an integer or a string"
        raise TypeError(msg)

    def _build_teams(self) -> list[Team]:
        """Take all assets and build list of teams."""
        team_names: set[str] = {p.team_name for p in self.players}

        teams: list[Team] = []
        for team in team_names:
            cur_players = tuple(p for p in self.players if p.team_name == team)
            cur_team = Team(
                assets=list(cur_players),
                name=team.strip(),
                lineup_setter=self.lineup_setter,
            )
            cur_team.set_lineup()
            teams.append(cur_team)
        return teams

    def _make_players_from_data(self) -> list[Asset]:
        """Instantiate players for each raw player returned from api."""
        return [
            Asset(
                _id=i["id"],
                team_name=i["team"],
                name=i["name"],
                pos=i["pos"],
                value=i["value"],
            )
            for i in self.player_data
        ]


class SleeperLeague(BaseLeague):
    def __init__(
        self, profile: dict, data_loc: str | Path, *, refresh_data: bool = False
    ):
        super().__init__(profile, refresh_data=refresh_data, data_loc=data_loc)

    def _download_data(self) -> list[_PlayerData]:
        import json

        import duckdb
        import requests

        try:
            # TODO: remove this
            # ! use this for dev only
            clean_player_data = pl.read_parquet(
                "tests/test_profiles/sleeper-players.parquet"
            )
        except FileNotFoundError:
            # Get all data:
            url = "https://api.sleeper.app/v1/players/nfl"
            resp = requests.get(url)
            content = resp.content.decode("utf-8")
            all_player_data: dict = json.loads(content)

            all_player_data_list = []  # reorient to list of dicts
            for id, player_data in all_player_data.items():
                cur_data = {"id": id, **player_data}
                all_player_data_list.append(cur_data)

            clean_player_data = pl.from_dicts(
                all_player_data_list, infer_schema_length=10_000
            ).select("player_id", "full_name", pos="position")

        league_id = self.profile["id"]

        # Get roster data:
        url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
        resp = requests.get(url)
        content = resp.content.decode("utf-8")
        roster_data: list[dict] = json.loads(content)
        clean_roster_data = (
            pl.from_dicts(roster_data)
            .select("owner_id", player_id="players")
            .explode("player_id")
        )

        joined_data = clean_roster_data.join(
            clean_player_data, how="inner", on="player_id"
        )

        # Join team names:
        url = f"https://api.sleeper.app/v1/league/{league_id}/users"
        resp = requests.get(url)
        content = resp.content.decode("utf-8")
        team_metadata: list[dict] = json.loads(content)
        user_team_lookup = (
            pl.from_dicts(team_metadata)
            .select("user_id", "metadata")
            .unnest("metadata")
            .select(
                pl.col("user_id").alias("owner_id"), pl.col("team_name").alias("team")
            )
        )

        with_team_name = (
            joined_data.join(user_team_lookup, on="owner_id")
            .drop("owner_id")
            .rename({"full_name": "name", "player_id": "id"})
        )

        # Get dynasty process values
        dynasty_values = (  # noqa: F841
            pl.read_csv(
                "https://github.com/dynastyprocess/data/raw/refs/heads/master/files/values-players.csv",
                infer_schema_length=10_000,
            )
            .select(
                pl.col("player").alias("name"),
                pl.col("value_2qb").alias("value"),
            )
            .sort("name", "value")
            .unique(subset=["name"], keep="first")
            .with_columns(pl.col("name").replace(KNOWN_PLAYER_MISMATCHES))
        )

        matched_players = duckdb.sql("""--sql
            SELECT *,
                jaro_winkler_similarity(with_team_name.name, dynasty_values.name) as _sim,
                ROW_NUMBER() OVER (PARTITION BY with_team_name.name ORDER BY _sim DESC) AS _rank,
                with_team_name.name as _alt_name
            FROM with_team_name
            JOIN dynasty_values
            ON jaro_winkler_similarity(with_team_name.name, dynasty_values.name) > .9
                    """).to_arrow_table()

        res = (
            pl.from_arrow(matched_players)
            .filter(pl.col("_rank") == 1)
            .drop("_sim", "_rank", "_alt_name")
        )

        missing_names = with_team_name.join(res, on="id", how="anti")
        if len(missing_names) > 0:
            click.secho(
                f"WARNING: Some players were not matched to values. --> {missing_names}",
                fg="red",
            )
        return res


class ESPNLeague(BaseLeague):
    def _download_data(self) -> list[_PlayerData]:
        """
        Get ESPN data.

        Args:
            league_id (int): _description_
            espn_s2 (str): _description_
            swid (str): _description_
            year (int, optional): _description_. Defaults to 2024.
        """
        import nfl_data_py as nfl
        from espn_api.football import League

        league = League(
            league_id=self.profile["id"],
            espn_s2=self.profile["espn_s2"],
            swid=self.profile["swid"],
            year=self.profile["year"],
            debug=True,
        )

        full_schedule = pl.DataFrame(nfl.import_schedules([self.profile["year"]]))
        cur_week: int = (
            full_schedule.filter(pl.col("result").is_null())
            .select(pl.col("week").min())
            .item()
        )
        teams_playing = (
            full_schedule.filter(pl.col("week") == cur_week)
            .select("away_team", "home_team")
            .unpivot()
            .select("value")
            .unique()
            .to_series()
            .to_list()
        )
        teams_playing = set(teams_playing)

        team_rosters: list = []
        for team in league.teams:
            roster: list = team.roster
            for player in roster:
                clean_player = _PlayerData(
                    id=player.playerId,
                    team=team.team_name,
                    name=player.name,
                    pos=player.position,
                    value=(player.percent_owned + player.percent_started) / 2,
                )
                team_rosters.append(clean_player)

        return team_rosters

    def __init__(
        self, profile: dict, data_loc: str | Path, *, refresh_data: bool = False
    ):
        super().__init__(profile, refresh_data=refresh_data, data_loc=data_loc)


PLATFORM_SWITCH = {"espn": ESPNLeague, "sleeper": SleeperLeague}
