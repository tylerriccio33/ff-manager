"""Building Trade Options."""

from __future__ import annotations

from src.classes import League
from src.data import get_data
from src.filter import PackageFilter, ReceiveFilter, SendFilter
from src.functions import (
    assemble_trades,
    loc_best_trades,
)
from src.utils import sink
from tqdm import tqdm

# kernprof -l -v main.py

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


def value_fn(dynasty_value: int, starter_value=None) -> int:  # noqa: ARG001
    return dynasty_value


def main() -> None:
    # Setup:
    raw_players, raw_picks = get_data(platform="sleeper", refresh=False)
    league = League(
        raw_player_data=raw_players,
        raw_pick_data=raw_picks,
        value_fn=value_fn,
    )

    # Filter API:
    send_filter = SendFilter(
        not_assets=("Garrett Wilson", "Zay Flowers"),
        team=league["Black Wilson"],
        min_asset_value=100,
    )

    receive_filter = ReceiveFilter(
        min_asset_value=100,
        does_not_contain_pos=("wr",),
    )

    package_filter = PackageFilter(max_assets=2, return_contains=("Josh Downs",))

    # Assemble and Execute Trades:
    trades = assemble_trades(
        send_filter=send_filter,
        receive_filter=receive_filter,
        package_filter=package_filter,
        league=league,
    )
    for trade in tqdm(trades, "Executing Trades: "):
        trade.execute_trade()

    # Loc Best Trades:
    best_trades = loc_best_trades(
        trades=trades,
        max_fleece=1000,
        min_gain=0,
        max_gap=1000,
    )

    # Sink Results:
    sink(best_trades)


if __name__ == "__main__":
    main()
