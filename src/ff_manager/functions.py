"""Functions supporting the trade engine."""

from __future__ import annotations

import contextlib
import itertools
from typing import TYPE_CHECKING

import numpy as np
from tqdm import tqdm

from ff_manager.trade import Package, Trade

if TYPE_CHECKING:
    from ff_manager.filter import PackageFilter, ReceiveFilter, SendFilter
    from ff_manager.league import League, Team


def assemble_trades(
    team: Team,
    send_filter: SendFilter,
    receive_filter: ReceiveFilter,
    package_filter: PackageFilter,
    league: League,
) -> list[Trade]:
    cur_packages = [
        Package(package)
        for length in range(package_filter.max_assets)
        for package in itertools.combinations(team.assets, length + 1)
    ]
    cur_packages: list[Package] = [
        package for package in cur_packages if send_filter(package)
    ]
    if not cur_packages:
        raise ValueError("No packages passed the send filter.")

    opp_team_names: set[str] = package_filter.get_matching_teams(
        league_assets=league.assets
    )
    with contextlib.suppress(KeyError):  # passed singular opp team
        opp_team_names.remove(team.name)
    opp_teams: list[Team] = [league[team_name] for team_name in opp_team_names]
    # TODO: why not just use opp_team_names ?

    if not opp_teams:
        raise ValueError("No opposing teams with trade candidates found.")

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
                team1=team,
                team2=opp,
                package1=team_one_package,
                package2=team_two_package,
                lineup_setter=league.lineup_setter,
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
        raise ValueError("No trades passed the package or receive filters.")
    return flattened


def loc_best_trades(
    trades: list[Trade],
    max_fleece: float | None = None,
    min_gain: float | None = 0,
    *,
    sort_trades: bool = True,
) -> list[Trade]:
    """Return indices of positive trade values."""
    # Pull Gains as Vectors:
    trade_gain1: np.ndarray = np.fromiter(
        (trade.team1_gain for trade in trades),
        dtype=float,
    )
    trade_gain2: np.ndarray = np.fromiter(
        (trade.team2_gain for trade in trades),
        dtype=float,
    )

    # Stack gains and add index in 3rd position
    trade_val_mat = np.stack((trade_gain1, trade_gain2), axis=1)
    indices = np.arange(len(trades), dtype=int).reshape(-1, 1)
    mat = np.hstack((trade_val_mat, indices))

    # Filter Checks:
    if min_gain is not None:
        valid_value_added_i = np.where(mat[:, 0] >= min_gain)[0]
        mat = mat[valid_value_added_i]

    if max_fleece is not None:
        value_gap = np.abs(mat[:, 0] - mat[:, 1])  # use already filtered matrix
        valud_value_gap_i = np.flatnonzero(value_gap < max_fleece)
        mat = mat[valud_value_gap_i]

    # Sort:
    if sort_trades:
        sort_i = np.argsort(-mat[:, 0])
        mat = mat[sort_i, :]

    # Subset:
    valid_trade_i = mat[:, 2]
    print(f"Located {len(valid_trade_i)} trades!")
    return [trades[int(i)] for i in valid_trade_i]
