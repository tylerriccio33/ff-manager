"""Building Trade Options."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from tqdm import tqdm

from ff_manager.filter import PackageFilter, ReceiveFilter, SendFilter
from ff_manager.functions import (
    assemble_trades,
    loc_best_trades,
)
from ff_manager.utils import ingest_reqs

if TYPE_CHECKING:
    from ff_manager.model import Trade


def eval_trades(league, reqs: str | Path | dict) -> list[Trade] | None:
    """Evaluate trades, given filter constaints and a value function."""
    if isinstance(reqs, str | Path):
        with Path(reqs).open() as f:
            reqs_loaded = defaultdict(lambda: None) | yaml.safe_load(f)
    else:
        reqs_loaded = reqs
    reqs_loaded = ingest_reqs(reqs_loaded)

    send_filter = SendFilter(**reqs_loaded)
    receive_filter = ReceiveFilter(**reqs_loaded)
    package_filter = PackageFilter(**reqs_loaded)

    # Assemble and Execute Trades:
    trades = assemble_trades(
        team=league[reqs_loaded["team"]],
        send_filter=send_filter,
        receive_filter=receive_filter,
        package_filter=package_filter,
        league=league,
    )
    for trade in tqdm(trades, "Executing Trades: "):
        trade.execute_trade()

    # Loc Best Trades:
    return loc_best_trades(
        trades=trades,
        max_fleece=reqs_loaded["max_fleece"],
        min_gain=0,
    )


def main(
    reqs: str | Path,
    profile: str | Path,
    data: str | Path | None = None,
    sink_to: str | Path | None = None,
) -> None:
    with Path(reqs).open() as f:
        reqs_loaded = defaultdict(lambda: None) | yaml.safe_load(f)

    reqs_loaded = ingest_reqs(reqs_loaded)

    with Path(profile).open() as f:
        prof_loaded: dict = yaml.safe_load(f)

    if reqs_loaded["refresh_data"]:
        from ff_manager.data import get_espn_data, get_sleeper_data

        platform = prof_loaded["platform"]
        if platform == "sleeper":
            get_sleeper_data(league_id=prof_loaded["id"], parquet_outfile=data)
        elif platform == "espn":
            get_espn_data(
                league_id=prof_loaded["id"],
                espn_s2=prof_loaded["s2"],
                swid=prof_loaded["swid"],
                outfile=data,
            )
        else:
            raise ValueError("Platform must be sleepr or ESPN.")

    loaded_data: list[dict] = get_data(data)  # noqa: F821

    trades = _main(  # noqa: F821
        reqs=reqs_loaded, prof=prof_loaded, data=loaded_data, sink_to=sink_to
    )
    if sink_to:
        with Path(sink_to).open("w") as f:
            original_stdout = sys.stdout
            sys.stdout = f
            print(trades)  # print to the subprocess
            sys.stdout = original_stdout
