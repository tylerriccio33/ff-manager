from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Container

from src.exception import NoValuesError

if TYPE_CHECKING:
    from src.classes import Asset


def get_team_from_assets(
    all_assets: Container[Asset],
    valid_assets: Container[Asset],
) -> set[str]:
    valid_assets = [asset for asset in all_assets if asset in valid_assets]

    teams = {asset.team_name for asset in valid_assets}

    if len(teams) == 0:
        raise NoValuesError(obj_name="opp teams")

    return teams


def get_team_from_pos(
    all_assets: Container[Asset],
    valid_pos: Container[str],
) -> set[str]:
    valid_assets = [asset for asset in all_assets if asset.pos in valid_pos]

    teams = {asset.team_name for asset in valid_assets}

    if len(teams) == 0:
        raise NoValuesError(obj_name="opp teams")

    return teams


def _correct_fuzzy_team_names(invalid_names: set, valid_names: set) -> dict:
    invalid_names_list = list(invalid_names)
    valid_names_list = list(valid_names)

    def _cleaner(val: str) -> str:
        new_val = re.sub(r"<[^>]*>", "", val)
        return " ".join(new_val.split())

    def _cleaner2(val: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", val)

    clean_valids = [_cleaner(valid_name) for valid_name in valid_names_list]

    name_map = {}
    # TODO: replace with contextlib
    for name in invalid_names_list:
        try:
            valid_name_i = valid_names_list.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            valid_name_i = clean_valids.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            clean_name = _cleaner(name)
            valid_name_i = clean_valids.index(clean_name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            cleaner_valids = [_cleaner2(valid_name) for valid_name in clean_valids]
            valid_name_i = cleaner_valids.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            cleaner_name = _cleaner2(name)
            valid_name_i = cleaner_valids.index(cleaner_name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass

        raise ValueError(f"Could not map {name}")  # noqa: TRY003

    return name_map


def sink(obj, fname="trade-prospects.txt", *, alert=True):
    if not obj:
        raise NoValuesError("trades")
    with Path.open("trade-prospects.txt", "w") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        print(obj)  # print to the subprocess
        sys.stdout = original_stdout
    if alert:
        print(f"Check the `{fname} file.")
