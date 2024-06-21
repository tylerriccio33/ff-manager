

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Callable, Dict, List

import numpy as np
import pandas as pd

from src.classes import DynastyValue, StarterValue
from src.utils import _correct_fuzzy_team_names

RawPlayers = List[Dict]
RawPicks = List[Dict]


class _RScriptError(Exception):
    def __init__(self):
        super().__init__("R script failed to execute.")


def _get_sleeper_picks(*, refresh=False) -> list[dict]:
    if refresh:
        raise NotImplementedError("Just run the pyscript")
    fpath = "app/data/sleeper/draft_table_appended.csv"
    pick_data = pd.read_csv(fpath)
    pick_data = pick_data.rename(columns={"value_2qb": "dynasty_value"})
    pick_data = pick_data[["team", "pick_number", "dynasty_value"]]
    return pick_data.to_dict("records")


def get_sleeper_data(*, refresh=False) -> tuple[RawPlayers, RawPicks]:
    import json

    # Refresh Data:
    if refresh:
        import subprocess

        fpath = "src/data/sleeper/data.R"
        try:
            subprocess.run(["Rscript", fpath], check=True)
        except subprocess.CalledProcessError as e:
            raise _RScriptError from e

    # Load Data:
    with Path.open("app/data/sleeper_assets.json") as f:
        data = json.load(f)

    # Post Processing:
    for asset in data:
        if "starter_value" not in asset:
            asset["starter_value"] = 0
        if "dynasty_value" not in asset:
            asset["dynasty_value"] = 0

    players = [asset for asset in data if not asset.get("pick_number")]

    # New Get Picks:
    picks: list[dict] = _get_sleeper_picks(refresh=False)

    # Correct Team Names:
    # - the team names are imperfect
    name_map: dict = _correct_fuzzy_team_names(
        invalid_names={pick["team"] for pick in picks},
        valid_names={player["team"] for player in players},
    )
    for pick in picks:
        new_name = name_map[pick["team"]]
        pick["team"] = new_name
        pick["id"] = pick["pick_number"]

    return (players, picks)


def get_data(platform="sleeper", **kwargs) -> tuple[RawPlayers, RawPicks]:
    # TODO: check fields are all good upon return

    platform_fn_map = {"sleeper": get_sleeper_data}

    try:
        return platform_fn_map[platform](**kwargs)
    except KeyError:
        raise NotImplementedError(f"Platform {platform} is not implemented") from None


def gen_value_fn(
    raw_players,
    raw_picks,
) -> Callable[[DynastyValue, StarterValue], float]:
    """create function that converts dynasty, starter to composite"""

    assets = raw_players + raw_picks

    starter_vals = [asset["starter_value"] for asset in assets]
    dynasty_vals = [asset["dynasty_value"] for asset in assets]

    min_starter = np.min(starter_vals)
    max_starter = np.max(starter_vals)
    scalar_starter = max_starter - min_starter
    min_dynasty = np.min(dynasty_vals)
    max_dynasty = np.max(dynasty_vals)
    scalar_dynasty = max_dynasty - min_dynasty

    def _avg_value(
        dynasty_value: float,
        starter_value: float,
        _min_starter,
        _scalar_starter,
        _min_dynasty,
        _scalar_dynasty,
    ) -> float:
        normal_starter = (dynasty_value - _min_dynasty) / _scalar_starter
        normal_dynasty = (starter_value - _min_starter) / _scalar_dynasty
        return (normal_starter + normal_dynasty) / 2

    return partial(
        _avg_value,
        _min_starter=min_starter,
        _scalar_starter=scalar_starter,
        _min_dynasty=min_dynasty,
        _scalar_dynasty=scalar_dynasty,
    )
