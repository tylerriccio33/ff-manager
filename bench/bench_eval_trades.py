from __future__ import annotations

import pytest

from ff_manager.api import eval_trades

BASE_REQS: dict = {
    "team": "alpha",
    "max_fleece": 20,
    "min_asset_value": 40,
}


@pytest.mark.parametrize("max_assets", [1, 2, 3])
@pytest.mark.parametrize("filtered", [False, True], ids=["nofilter", "filtered"])
@pytest.mark.parametrize("scope", ["all", "single"])
def test_bench_eval_trades(benchmark, league_10team, max_assets, filtered, scope):
    reqs: dict = {**BASE_REQS, "max_assets": max_assets}
    if filtered:
        reqs["target_pos"] = "RB"
    if scope == "single":
        reqs["assets_from_team"] = "bravo"

    def run():
        result = eval_trades(league=league_10team, reqs=reqs)
        assert len(result) > 0
        return result

    benchmark(run)
