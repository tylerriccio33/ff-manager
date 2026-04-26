"""Building Trade Options."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from tqdm import tqdm

from ff_manager.filter import PackageFilter, ReceiveFilter, SendFilter
from ff_manager.functions import assemble_trades, loc_best_trades
from ff_manager.utils import ingest_reqs

if TYPE_CHECKING:
    from ff_manager.trade import Trade


def eval_trades(league, reqs: str | Path | dict) -> list[Trade]:
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
    data_loc: str | Path,
    *,
    refresh_data: bool = False,
) -> list[Trade]:
    """Load profile + data, build the configured league, and evaluate trades."""
    from ff_manager.league import PLATFORM_SWITCH

    with Path(profile).open() as f:
        prof_loaded: dict = yaml.safe_load(f)

    league_cls = PLATFORM_SWITCH[prof_loaded["platform"]]
    league = league_cls(
        profile=prof_loaded, data_loc=data_loc, refresh_data=refresh_data
    )
    return eval_trades(league=league, reqs=reqs)
