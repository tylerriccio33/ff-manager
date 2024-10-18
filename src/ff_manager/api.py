"""Building Trade Options."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from tqdm import tqdm

from ff_manager.data import get_data
from ff_manager.filter import PackageFilter, ReceiveFilter, SendFilter
from ff_manager.functions import (
    assemble_trades,
    loc_best_trades,
)
from ff_manager.league import League
from ff_manager.utils import ingest_reqs

if TYPE_CHECKING:
    from ff_manager.league import Trade


""" PRIORITY ORDER:
    Move some things like asset, league, etc. to a model file
    Distance From Lineup Decay:
        - decay value with proximity
    Basic Testing Plan:
        - lineup optimizer
        - trade assembler respects filters
        - basic end to ends
            - return trades sending the 1st overall
            - trades for a qb/super
    Position/Lineup Overhaul:
        - system of positions, slot categories and specific slots
        - pos manager seems useful but should be fleshed out
        - seamless handling of no/any postion for picks
        - move specific position handling away from Asset subclasses
    Abstract to Different Files:
        - move everything to different files
        - this is feeling more like a monolith
    Web UI
"""


def eval_trades(
    team: str,
    send_filter: SendFilter,
    receive_filter: ReceiveFilter,
    package_filter: PackageFilter,
    max_fleece: float,
    profile: Path | str | dict,
    data,
) -> list[Trade] | None:
    """
    Evaluate trades, given filter constaints and a value function..

    Args:
    ----
        send_filter (SendFilter): _description_
        receive_filter (ReceiveFilter): _description_
        package_filter (PackageFilter): _description_
        platform (str, optional): _description_. Defaults to "sleeper".
    """
    if isinstance(profile, dict):
        loaded_profile = profile
    else:
        with Path(profile).open() as f:
            loaded_profile: dict = yaml.safe_load(f)
    league = League(
        raw_player_data=data,
        profile=loaded_profile,
    )

    # Assemble and Execute Trades:
    trades = assemble_trades(
        team=league[team],
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
        max_fleece=max_fleece,
        min_gain=0,
    )


def _main(
    reqs: dict, prof: dict, data: str | Path, sink_to: str | Path | None = None
) -> list[Trade]:
    send_filter = SendFilter(
        **reqs,
    )
    receive_filter = ReceiveFilter(**reqs)
    package_filter = PackageFilter(**reqs)

    trades = eval_trades(
        team=reqs["team"],
        send_filter=send_filter,
        receive_filter=receive_filter,
        package_filter=package_filter,
        profile=prof,
        data=data,
        max_fleece=reqs["max_fleece"],
    )

    if sink_to:
        with Path(sink_to).open("w") as f:
            original_stdout = sys.stdout
            sys.stdout = f
            print(trades)  # print to the subprocess
            sys.stdout = original_stdout
    return trades


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

    loaded_data: list[dict] = get_data(data)

    return _main(reqs=reqs_loaded, prof=prof_loaded, data=loaded_data, sink_to=sink_to)
