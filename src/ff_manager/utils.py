from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from ff_manager.const import REQUIRED_REQ_FIELDS

if TYPE_CHECKING:
    from collections.abc import Iterable

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


def containerize_str(val: str | Iterable[str] | None) -> tuple[str, ...] | None:
    if val is None:
        return None
    if isinstance(val, str):
        return (val,)
    return tuple(val)


def diff_assets(assets: Iterable[Asset], rm: Iterable[Asset]) -> tuple[Asset, ...]:
    valid_assets = list(assets)
    for asset in rm:
        valid_assets.remove(asset)
    return tuple(valid_assets)


def ingest_reqs(reqs: dict) -> dict:
    for field in REQUIRED_REQ_FIELDS:
        if field not in reqs:
            raise ValueError(f"The key {field} must be in the reqs.")

    return {k.replace("-", "_"): v for k, v in reqs.items()}


def sink_repr(obj: Iterable, sink_to: str | Path, *, iter_obj: bool = True) -> None:
    with Path(sink_to).open("w") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        concatenated: str = "\n".join(str(obj) for obj in obj)
        print(concatenated)
        sys.stdout = original_stdout
