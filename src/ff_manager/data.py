from __future__ import annotations

import contextlib
import json
from pathlib import Path

import click
import duckdb
import polars as pl
from espn_api.football import League

from ff_manager.const import KNOWN_PLAYER_MISMATCHES


def get_data(loc: str | Path) -> list[dict]:
    # TODO: describe and validate protocol for return

    methods = [
        pl.read_parquet,
        pl.read_json,
        pl.read_csv,
    ]
    for method in methods:
        with contextlib.suppress(FileNotFoundError, pl.exceptions.ComputeError):
            return method(loc).to_dicts()

    raise FileNotFoundError(f"Could not find {loc!s}")


def get_sleeper_data(league_id: int, parquet_outfile: Path | str) -> None:
    import json

    import polars as pl
    import requests

    try:
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

    joined_data = clean_roster_data.join(clean_player_data, how="inner", on="player_id")

    # Join team names:
    url = f"https://api.sleeper.app/v1/league/{league_id}/users"
    resp = requests.get(url)
    content = resp.content.decode("utf-8")
    team_metadata: list[dict] = json.loads(content)
    user_team_lookup = (
        pl.from_dicts(team_metadata)
        .select("user_id", "metadata")
        .unnest("metadata")
        .select(pl.col("user_id").alias("owner_id"), pl.col("team_name").alias("team"))
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
    res.write_parquet(parquet_outfile)


def get_espn_data(
    league_id: int, espn_s2: str, swid: str, outfile: Path | str, year=2024
) -> None:
    """
    Get ESPN data.

    Args:
        league_id (int): _description_
        espn_s2 (str): _description_
        swid (str): _description_
        year (int, optional): _description_. Defaults to 2024.
    """
    import nfl_data_py as nfl

    league = League(
        league_id=league_id, espn_s2=espn_s2, swid=swid, year=year, debug=True
    )

    full_schedule = pl.DataFrame(nfl.import_schedules([year]))
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

    # raise NotImplementedError("What should we do with pct started if they're on bye.")
    team_rosters: list = []
    for team in league.teams:
        roster: list = team.roster
        for player in roster:
            clean_player = {
                "id": player.playerId,
                "team": team.team_name,
                "name": player.name,
                "pos": player.position,
                "value": (player.percent_owned + player.percent_started) / 2,
            }
            team_rosters.append(clean_player)

    json_str = json.dumps(team_rosters)
    with Path(outfile).open("w") as f:
        f.write(json_str)
