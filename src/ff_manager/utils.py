from __future__ import annotations

import contextlib
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from ff_manager.const import REQUIRED_REQ_FIELDS

if TYPE_CHECKING:
    from collections.abc import Container

    from ff_manager.model import Asset


def hierarchical_data_load(loc: str | Path) -> list[dict]:
    methods = [
        pl.read_parquet,
        pl.read_json,
        pl.read_csv,
    ]
    for method in methods:
        with contextlib.suppress(FileNotFoundError, pl.exceptions.ComputeError):
            return method(loc).to_dicts()

    raise FileNotFoundError(f"Could not find {loc!s}")


def containerize_str(val: str | Container[str]) -> Container[str]:
    if isinstance(val, str):
        return (val,)
    return val


def diff_assets(assets: list[Asset], rm: list[Asset]) -> tuple:
    valid_assets = assets.copy()
    for asset in rm:
        valid_assets.remove(asset)
    return tuple(valid_assets)


def ingest_reqs(reqs: dict) -> dict:
    for field in REQUIRED_REQ_FIELDS:
        if field not in reqs:
            raise ValueError(f"The key {field} must be in the reqs.")

    return {k.replace("-", "_"): v for k, v in reqs.items()}


def sink_repr(obj: object, sink_to: str | Path) -> None:
    with Path(sink_to).open("w") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        print(obj)
        sys.stdout = original_stdout


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
    for name in invalid_names_list:
        with contextlib.suppress(ValueError):
            valid_name_i = valid_names_list.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue

        with contextlib.suppress(ValueError):
            valid_name_i = clean_valids.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue

        with contextlib.suppress(ValueError):
            clean_name = _cleaner(name)
            valid_name_i = clean_valids.index(clean_name)
            name_map[name] = valid_names_list[valid_name_i]
            continue

        with contextlib.suppress(ValueError):
            cleaner_valids = [_cleaner2(valid_name) for valid_name in clean_valids]
            valid_name_i = cleaner_valids.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue

        with contextlib.suppress(ValueError):
            cleaner_name = _cleaner2(name)
            valid_name_i = cleaner_valids.index(cleaner_name)
            name_map[name] = valid_names_list[valid_name_i]
            continue

        raise ValueError(f"Could not map {name}")

    return name_map
