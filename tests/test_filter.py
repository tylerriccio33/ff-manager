import json
from pathlib import Path

import pytest

from ff_manager.api import _main


def _check_2qb(res) -> None:
    """Bank all checks in one spot; only 1 real possible result."""
    assert len(res) == 1
    cur_trade = res[0]

    assert cur_trade.new_team1_value == cur_trade.new_team2_value
    assert cur_trade.new_team1_value == 5
    assert cur_trade.team1_gain == 0
    assert cur_trade.team2_gain == 0

    assert cur_trade.sent_assets[0].pos == "QB"
    assert cur_trade.rec_assets[0].pos == "QB"

    assert cur_trade.sent_assets[0].name == "player-0"
    assert cur_trade.rec_assets[0].name == "player-1"


def _conf_test(prof: str | Path, data: str | Path, reqs) -> list:
    with Path(prof).open() as fpath:
        prof = json.load(fpath)
    with Path(data).open() as fpath:
        data = json.load(fpath)
    return _main(reqs=reqs, prof=prof, data=data)


def test_same_value():
    reqs = {"team": "team1", "max_fleece": 5, "target_pos": "QB"}

    trades = _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)
    _check_2qb(trades)


def test_send_pos_good():
    reqs = {"team": "team1", "max_fleece": 5, "pos": "QB", "target_pos": "QB"}
    trades = _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)
    _check_2qb(trades)


def test_assets_not_from_team_and_pos():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "pos": "QB",
        "assets_not_from_team": "team2",
    }
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/3team1.json", reqs
    )
    for trade in trades:
        for asset in trade.rec_assets:
            assert asset.team_name != "team2"
            assert asset.pos == "QB"


def test_return_contains1():
    reqs = {"team": "team1", "max_fleece": 5, "return_contains": ["player-1"]}
    trades = _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)
    _check_2qb(trades)


def test_return_not_contains_pos():
    reqs = {"team": "team1", "max_fleece": 5, "return_not_pos": ["QB"]}
    with pytest.raises(
        ValueError, match="No trades passed the package or receive filters."
    ):
        _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)


def test_return_contains2():
    reqs = {"team": "team1", "max_fleece": 5, "return_contains": ["player-2"]}
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs
    )
    assert trades
    for trade in trades:
        assert any(asset for asset in trade.rec_assets if asset.name == "player-2")


def test_return_contains_bad1():
    reqs = {"team": "team1", "max_fleece": 5, "return_contains": ["player-99"]}
    with pytest.raises(
        ValueError,
        match="No opposing teams with trade candidates found.",
    ):
        _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)


def test_send_pos_bad():
    reqs = {"team": "team1", "max_fleece": 5, "pos": "RB", "target_pos": "QB"}
    with pytest.raises(ValueError, match="No packages passed the send filter."):
        _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)


def test_send_assets1():
    reqs = {"team": "team1", "max_fleece": 5, "assets": "player-0", "target_pos": "QB"}
    trades = _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)
    _check_2qb(trades)


def test_not_assets1():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "not_assets": "player-0",
        "target_pos": "QB",
    }
    with pytest.raises(ValueError, match="No packages passed the send filter."):
        _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb.json", reqs)


def test_send_assets2():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "assets": "player-0",  # Package must contain player-0
        "target_pos": "QB",
    }
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs
    )

    assert trades
    for trade in trades:
        assert trade.sent_assets[0].name != "player-2"


def test_min_asset_value1():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "target_pos": "QB",
        "min_asset_value": 1,
    }
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs
    )
    assert trades
    for trade in trades:
        for asset in trade.sent_assets:
            assert asset.value >= 1
        for asset in trade.rec_assets:
            assert asset.value >= 1


def test_min_asset_value_rm1():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "min_asset_value": 6,
    }

    with pytest.raises(ValueError, match="No packages passed the send filter."):
        _conf_test("tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs)


def test_assets_from_team1():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "assets_from_team": "team2",
        "target_pos": "QB",
    }
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs
    )
    assert trades
    for trade in trades:
        for asset in trade.rec_assets:
            assert asset.team_name == "team2"


@pytest.mark.parametrize("asset_len", [1, 2])
def test_max_assets(asset_len: int):
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "max_assets": asset_len,
        "target_pos": "QB",
    }
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs
    )
    for trade in trades:
        assert len(trade.sent_assets) <= asset_len
        assert len(trade.rec_assets) <= asset_len


def test_not_contains_pos():
    reqs = {
        "team": "team1",
        "max_fleece": 5,
        "not_receive_pos": "RB",
        "target_pos": "QB",
    }
    trades = _conf_test(
        "tests/data/sleeper-super1.json", "tests/data/2qb-extra.json", reqs
    )
    for trade in trades:
        assert any(asset for asset in trade.rec_assets if asset.pos != "RB")


if __name__ == "__main__":
    test_return_not_contains_pos()
