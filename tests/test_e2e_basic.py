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

from ff_manager.api import eval_trades
from ff_manager.trade import Trade


def test_baseline_qb2_for_rb3(league_basic):
    reqs = {
        "team": "team1",
        "max_fleece": 20,
        "min_asset_value": 40,
        "max_assets": 1,
    }

    # Pre-trade lineup sanity (exercises league build + lineup setter).
    team1 = league_basic["team1"]
    team2 = league_basic["team2"]
    assert team1.set_lineup().total_value == 490
    assert team2.set_lineup().total_value == 450

    trades = eval_trades(league=league_basic, reqs=reqs)

    # The top-ranked trade (highest team1_gain) is QB2-for-RB3.
    # Lesser positive-gain trades may also pass; we don't assert on them here.
    assert len(trades) >= 1
    trade = trades[0]
    assert isinstance(trade, Trade)
    # No other trade ties the top gain — uniquely the best.
    assert all(t.team1_gain < trade.team1_gain for t in trades[1:])

    # Identities of teams and assets.
    assert trade.team1.name == "team1"
    assert trade.team2.name == "team2"
    assert [a.name for a in trade.sent_assets] == ["T1-QB2"]
    assert [a.name for a in trade.rec_assets] == ["T2-RB3"]

    # Pre-trade values.
    assert trade.team1.lineup is not None
    assert trade.team2.lineup is not None
    assert trade.team1.lineup.total_value == 490
    assert trade.team2.lineup.total_value == 450

    # Post-trade values.
    assert trade.new_team1_value == 522
    assert trade.new_team2_value == 463

    # Gains.
    assert trade.team1_gain == 32
    assert trade.team2_gain == 13

    # Fleece is within bound (strict <, per loc_best_trades).
    assert abs(trade.team1_gain - trade.team2_gain) < reqs["max_fleece"]

    # Roster invariants: each team's post-trade asset count is preserved.
    assert len(list(trade.new_team1.assets)) == len(list(team1.assets))
    assert len(list(trade.new_team2.assets)) == len(list(team2.assets))

    # Sent asset is gone from new team1; received asset is present.
    new_t1_names = {a.name for a in trade.new_team1.assets}
    assert "T1-QB2" not in new_t1_names
    assert "T2-RB3" in new_t1_names

    new_t2_names = {a.name for a in trade.new_team2.assets}
    assert "T2-RB3" not in new_t2_names
    assert "T1-QB2" in new_t2_names

    # Lineup composition for new team1: QB1 keeps QB slot; T2-RB3 starts at RB.
    assert trade.new_team1.lineup is not None
    assert trade.new_team2.lineup is not None
    new_t1_lineup_names = {p.name for p in trade.new_team1.lineup.data.values()}
    assert "T1-QB1" in new_t1_lineup_names
    assert "T2-RB3" in new_t1_lineup_names
    assert "T1-QB2" not in new_t1_lineup_names

    # Lineup composition for new team2: T1-QB2 takes QB slot.
    new_t2_lineup_names = {p.name for p in trade.new_team2.lineup.data.values()}
    assert "T1-QB2" in new_t2_lineup_names
    assert "T2-RB3" not in new_t2_lineup_names
