"""Functions supporting the trade engine."""

from __future__ import annotations

import contextlib
import itertools
from typing import TYPE_CHECKING

import numpy as np
from tqdm import tqdm

from src.classes import League, Package, Team, Trade
from src.exception import NoValuesError

if TYPE_CHECKING:
    from src.filter import PackageFilter, ReceiveFilter, SendFilter


def assemble_trades(
    send_filter: SendFilter,
    receive_filter: ReceiveFilter,
    package_filter: PackageFilter,
    league: League,
) -> list[Trade]:
    # Assemble All Current Packages:
    all_available_assets = send_filter.all_team_assets
    cur_packages = [
        Package(package)
        for length in range(package_filter.max_assets)
        for package in itertools.combinations(all_available_assets, length + 1)
    ]
    cur_packages: list[Package] = [
        package for package in cur_packages if send_filter(package)
    ]
    if not cur_packages:
        raise NoValuesError("packages")

    opp_team_names: set[str] = package_filter.get_opp_teams(league_assets=league.assets)
    opp_teams: list[Team] = [league[team_name] for team_name in opp_team_names]
    trades: list[list[Trade]] = []
    for opp in tqdm(opp_teams):
        print(f"Building trades for <{opp}>")

        opp_packages: list[Package] = [
            Package(package)
            for length in range(package_filter.max_assets)
            for package in itertools.combinations(opp.assets, length + 1)
        ]

        # Package Filter:
        with contextlib.suppress(TypeError):
            opp_packages = [
                package for package in opp_packages if package_filter(package)
            ]

        # Receive Filter:
        with contextlib.suppress(TypeError):
            opp_packages = [
                package for package in opp_packages if receive_filter(package)
            ]

        # Assemble Trades:
        package_iter = itertools.product(cur_packages, opp_packages)
        cur_trades = [
            Trade(
                team1=send_filter.team,
                team2=opp,
                package1=team_one_package,
                package2=team_two_package,
            )
            for (team_one_package, team_two_package) in tqdm(
                package_iter,
                "Assembling Trades.",
            )
        ]
        trades.append(cur_trades)

    # Flatten Trades:
    flattened = list(itertools.chain.from_iterable(trades))
    if not flattened:
        raise NoValuesError("trades")
    return flattened


def loc_best_trades(
    trades: list[Trade],
    max_fleece: float | None = None,
    min_gain: float | None = 0,
    max_gap: float | None = 500,
    *,
    sort_trades: bool = True,
) -> list[Trade]:
    """return indices of positive trade values"""

    if not trades:
        raise NoValuesError("trades")

    # Pull Gains as Vectors:
    trade_gain1: np.ndarray = np.fromiter(
        (trade.team1_gain for trade in trades),
        dtype=int,
    )
    trade_gain2: np.ndarray = np.fromiter(
        (trade.team2_gain for trade in trades),
        dtype=int,
    )

    # Stack as Matrix:
    trade_val_mat = np.stack((trade_gain1, trade_gain2), axis=1)
    indices = np.arange(len(trades), dtype=int).reshape(-1, 1)
    mat = np.hstack((trade_val_mat, indices))

    # Filter Checks:
    if min_gain is not None:
        valid_value_added_i = np.where(mat[:, 0] > min_gain)[0]
        mat = mat[valid_value_added_i]

    if max_fleece is not None:
        valid_value_added_i = np.where(mat[:, 1] > -max_fleece)[0]
        mat = mat[valid_value_added_i]

    if max_gap is not None:
        abs_gap = np.abs(mat[:, 0] - mat[:, 1])
        mat = mat[abs_gap <= max_gap]

    # Sort:
    if sort_trades:
        sort_i = np.argsort(-mat[:, 0])
        mat = mat[sort_i, :]

    # Subset:
    valid_trade_i = mat[:, 2]
    print(f"Located {len(valid_trade_i)} trades!")
    return [trades[i] for i in valid_trade_i]



