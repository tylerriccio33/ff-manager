"""
Reusable assertions for end-to-end trade tests.

`assert_trade_invariants` checks the structural properties any valid
`Trade` should satisfy regardless of fixture or filter config. Use it
as guardrails inside specific edge-case tests so they stay focused on
the dimension under test instead of re-asserting basic correctness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ff_manager.trade import Trade


def assert_trade_invariants(
    trade: Trade,
    *,
    max_fleece: float | None = None,
    min_gain: float | None = 0,
) -> None:
    """Properties any valid Trade returned from eval_trades must satisfy."""
    # Distinct teams.
    assert trade.team1.name != trade.team2.name

    # Roster size accounting: |new| = |old| - sent + received per team.
    sent_n = len(trade.sent_assets)
    rec_n = len(trade.rec_assets)
    old_t1 = list(trade.team1.assets)
    old_t2 = list(trade.team2.assets)
    new_t1 = list(trade.new_team1.assets)
    new_t2 = list(trade.new_team2.assets)
    assert len(new_t1) == len(old_t1) - sent_n + rec_n
    assert len(new_t2) == len(old_t2) - rec_n + sent_n

    # Asset movement: every sent asset left team1 and arrived at team2; vice versa.
    new_t1_names = {a.name for a in new_t1}
    new_t2_names = {a.name for a in new_t2}
    for a in trade.sent_assets:
        assert a.name not in new_t1_names
        assert a.name in new_t2_names
    for a in trade.rec_assets:
        assert a.name in new_t1_names
        assert a.name not in new_t2_names

    # Lineup math is internally consistent.
    assert trade.team1.lineup is not None
    assert trade.team2.lineup is not None
    assert trade.new_team1.lineup is not None
    assert trade.new_team2.lineup is not None
    assert trade.new_team1_value == trade.new_team1.lineup.total_value
    assert trade.new_team2_value == trade.new_team2.lineup.total_value
    assert trade.team1_gain == trade.new_team1_value - trade.team1.lineup.total_value
    assert trade.team2_gain == trade.new_team2_value - trade.team2.lineup.total_value

    # Filter constraints respected.
    if min_gain is not None:
        assert trade.team1_gain >= min_gain
    if max_fleece is not None:
        # loc_best_trades uses strict `<` on the gap.
        assert abs(trade.team1_gain - trade.team2_gain) < max_fleece


def assert_results_invariants(
    trades: Iterable[Trade],
    *,
    max_fleece: float | None = None,
    min_gain: float | None = 0,
    expect_sorted: bool = True,
) -> list[Trade]:
    """Apply per-trade invariants to a result set and check ordering."""
    trade_list = list(trades)
    assert trade_list, "expected at least one trade in result set"
    for t in trade_list:
        assert_trade_invariants(t, max_fleece=max_fleece, min_gain=min_gain)
    if expect_sorted:
        gains = [t.team1_gain for t in trade_list]
        assert gains == sorted(gains, reverse=True)
    return trade_list
