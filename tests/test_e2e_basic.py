"""
End-to-end baseline test for the trade engine.

Builds a 3-team league from disk fixtures and runs the full
`eval_trades` pipeline. The roster is constructed so that exactly one
mutually-beneficial trade survives the configured filters: team1's
backup QB (T1-QB2, value 85) for team2's surplus RB at FLEX
(T2-RB3, value 72).

Pre-trade starting-lineup totals (1 QB / 2 RB / 2 WR / 1 TE / 2 FLEX):
    team1: 90 + 70+40 + 75+65 + 50 + 55+45 = 490
    team2: 30 + 80+78 + 60+50 + 45 + 72+35 = 450

Post-trade totals:
    team1: 90 + 72+70 + 75+65 + 50 + 55+45 = 522  (gain +32)
    team2: 85 + 80+78 + 60+50 + 45 + 35+30 = 463  (gain +13)

`max_assets=1` restricts the search to 1-for-1 trades, which makes
the (+32, +13) gain pair uniquely the top result. `max_fleece=20`
and `min_asset_value=40` prune nearby high-gain trades (e.g. trading
QB1 for T2-RB1 would gain +35 but fleece team2 by 25).
"""

from __future__ import annotations

import pytest

from ff_manager.api import eval_trades
from ff_manager.trade import Trade
from ff_manager.utils import sink_repr
from tests.helpers import assert_results_invariants, assert_trade_invariants

MAX_FLEECE = 20
BASELINE_REQS: dict = {
    "team": "team1",
    "max_fleece": MAX_FLEECE,
    "min_asset_value": 40,
    "max_assets": 1,
}


def test_baseline_qb2_for_rb3(league_basic):
    # Pre-trade lineup sanity (exercises league build + lineup setter).
    team1 = league_basic["team1"]
    team2 = league_basic["team2"]
    assert team1.set_lineup().total_value == 490
    assert team2.set_lineup().total_value == 450

    trades = eval_trades(league=league_basic, reqs=BASELINE_REQS)
    assert_results_invariants(
        trades,
        max_fleece=MAX_FLEECE,
        min_gain=0,
    )

    # The top-ranked trade (highest team1_gain) is QB2-for-RB3, uniquely.
    trade = trades[0]
    assert isinstance(trade, Trade)
    assert all(t.team1_gain < trade.team1_gain for t in trades[1:])

    # Exact-outcome assertions for the canonical trade.
    assert trade.team1.name == "team1"
    assert trade.team2.name == "team2"
    assert [a.name for a in trade.sent_assets] == ["T1-QB2"]
    assert [a.name for a in trade.rec_assets] == ["T2-RB3"]
    assert trade.new_team1_value == 522
    assert trade.new_team2_value == 463
    assert trade.team1_gain == 32
    assert trade.team2_gain == 13


def test_target_pos_rb_only(league_basic):
    """Receiving package must contain an RB; top trade still QB2-for-RB3."""
    reqs = {**BASELINE_REQS, "target_pos": "RB"}
    trades = eval_trades(league=league_basic, reqs=reqs)
    trades = assert_results_invariants(trades, max_fleece=MAX_FLEECE)

    for t in trades:
        assert any(a.pos == "RB" for a in t.rec_assets)

    top = trades[0]
    assert [a.name for a in top.sent_assets] == ["T1-QB2"]
    assert [a.name for a in top.rec_assets] == ["T2-RB3"]


def test_assets_from_team_only_team2(league_basic):
    """Restricting opponents to team2 still yields QB2-for-RB3 as best."""
    reqs = {**BASELINE_REQS, "assets_from_team": "team2"}
    trades = eval_trades(league=league_basic, reqs=reqs)
    trades = assert_results_invariants(trades, max_fleece=MAX_FLEECE)

    for t in trades:
        assert t.team2.name == "team2"

    top = trades[0]
    assert top.team1_gain == 32
    assert top.team2_gain == 13


def test_assets_not_from_team_team3(league_basic):
    """Excluding team3 leaves only team2 trades; baseline still wins."""
    reqs = {**BASELINE_REQS, "assets_not_from_team": "team3"}
    trades = eval_trades(league=league_basic, reqs=reqs)
    trades = assert_results_invariants(trades, max_fleece=MAX_FLEECE)

    for t in trades:
        assert t.team2.name != "team3"

    top = trades[0]
    assert [a.name for a in top.sent_assets] == ["T1-QB2"]
    assert [a.name for a in top.rec_assets] == ["T2-RB3"]


def test_return_contains_pins_target(league_basic):
    """`return_contains` forces every trade's receive package to include T2-RB3."""
    reqs = {**BASELINE_REQS, "return_contains": ["T2-RB3"]}
    trades = eval_trades(league=league_basic, reqs=reqs)
    trades = assert_results_invariants(trades, max_fleece=MAX_FLEECE)

    for t in trades:
        rec_names = [a.name for a in t.rec_assets]
        assert "T2-RB3" in rec_names

    top = trades[0]
    assert top.team1_gain == 32
    assert top.team2_gain == 13


def test_max_assets_two_allows_packages(league_basic):
    """
    Allowing 2-asset packages yields ties on top gain via bench-padded variants.

    The bench-padded duplicates produce identical (+32, +13) gains because
    the extra assets are below the lineup-relevance threshold. The helper
    still validates structural invariants on every trade.
    """
    reqs = {**BASELINE_REQS, "max_assets": 2}
    trades = eval_trades(league=league_basic, reqs=reqs)
    trades = assert_results_invariants(trades, max_fleece=MAX_FLEECE)

    # With 2-asset packages, larger gains become reachable (e.g. send
    # QB1+RB2 for T2-RB1 → +35/+20). The baseline 1-for-1 still appears
    # somewhere in the result set.
    top = trades[0]
    assert top.team1_gain >= 32
    assert any(
        [a.name for a in t.sent_assets] == ["T1-QB2"]
        and [a.name for a in t.rec_assets] == ["T2-RB3"]
        for t in trades
    )


def test_no_trades_when_target_pos_unsendable(league_basic):
    """Requiring receive-pos K (no kickers in fixture) yields no candidates."""
    reqs = {**BASELINE_REQS, "target_pos": "K"}
    with pytest.raises(ValueError, match="No trades passed"):
        eval_trades(league=league_basic, reqs=reqs)


def test_sink_results_to_disk(league_basic, tmp_path):
    """Final-stop check: trade results can be sunk to disk via sink_repr."""
    trades = eval_trades(league=league_basic, reqs=BASELINE_REQS)
    out = tmp_path / "trades.txt"
    sink_repr(trades, out)
    contents = out.read_text()
    assert contents.strip()
    assert contents.count("\n") >= len(trades) - 1


def test_helper_catches_invariant_violation(league_basic):
    """Sanity: the helper actually fails when invariants are broken."""
    trades = eval_trades(league=league_basic, reqs=BASELINE_REQS)
    trade = trades[0]
    # Corrupt the recorded gain; the helper must catch the inconsistency.
    original = trade.team1_gain
    trade.team1_gain = original + 1
    with pytest.raises(AssertionError):
        assert_trade_invariants(trade, max_fleece=MAX_FLEECE)
    trade.team1_gain = original
