"""Unit tests for ff_manager.api."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ff_manager.api import eval_trades, main

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def reqs_file(tmp_path: Path) -> Path:
    p = tmp_path / "reqs.yaml"
    p.write_text(
        yaml.safe_dump(
            {"team": "team1", "max_fleece": 20, "min_asset_value": 40, "max_assets": 1}
        )
    )
    return p


def test_eval_trades_with_path_reqs(league_basic, reqs_file: Path):
    trades = eval_trades(league=league_basic, reqs=reqs_file)
    assert trades
    assert trades[0].team1.name == "team1"


def test_eval_trades_with_str_reqs(league_basic, reqs_file: Path):
    trades = eval_trades(league=league_basic, reqs=str(reqs_file))
    assert trades


def test_main_end_to_end(tmp_path: Path, reqs_file: Path):
    # main() loads profile from disk and dispatches via PLATFORM_SWITCH.
    profile_path = DATA_DIR / "league_basic.profile.json"
    players_path = DATA_DIR / "league_basic.players.json"
    # main expects yaml-loadable profile; the json profile loads fine via yaml.
    trades = main(reqs=reqs_file, profile=profile_path, data_loc=players_path)
    assert trades
