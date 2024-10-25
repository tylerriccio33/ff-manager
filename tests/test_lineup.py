import pytest

from ff_manager.lineup import make_lineup_setter
from ff_manager.model import Asset


def test_very_horizontal_lineup():
    setter = make_lineup_setter(RB=1, depth=2)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
        Asset(name="player3", pos="RB", value=50),
        Asset(name="player4", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)

    assert lineup.total_value == 200
    assert lineup.starter_value == 100
    assert lineup.starter_keys == ["RB1"]

    lineup.pprint()


def test_very_horizontal_lineup2():
    setter = make_lineup_setter(RB=1, QB=1, depth=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="QB", value=100),
        Asset(name="player3", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)

    assert lineup.total_value == 250
    assert lineup.starter_value == 200
    assert lineup.starter_keys == ["RB1", "QB1"]

    lineup.pprint()


def test_pprint_no_error():
    setter = make_lineup_setter(RB=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    lineup.pprint()


def test_pprint_no_error_depth():
    setter = make_lineup_setter(RB=1, depth=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    lineup.pprint()


def test_starter_value_privacy():
    setter = make_lineup_setter(RB=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    with pytest.raises(AttributeError, match="Starter value is set upon"):
        lineup.starter_value = 0

    lineup.starter_value  # Is retrievable


def test_starter_keys_privacy():
    setter = make_lineup_setter(RB=1, depth=1)  # Only set if using depth
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    with pytest.raises(AttributeError, match="Starter keys is set upon"):
        lineup.starter_keys = 0

    lineup.starter_keys  # Is retrievable


def test_lineup_no_depth():
    setter = make_lineup_setter(RB=1, depth=0)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    assert lineup["RB1"] == "player1"

    assert lineup.starter_value == 100
    assert lineup.total_value == 100


def test_lineup_correct2():
    setter = make_lineup_setter(RB=1, FLEX=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    assert lineup["RB1"] == "player1"
    assert lineup["FLEX1"] == "player2"

    assert lineup.starter_value == 150
    assert lineup.total_value == 150


def test_lineup_backup():
    setter = make_lineup_setter(RB=2)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)
    assert lineup["RB1"] == "player1"
    assert lineup["RB2"] == "player2"

    assert lineup.starter_value == 150
    assert lineup.total_value == 150


def test_lineup_depth():
    setter = make_lineup_setter(RB=1, depth=2)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
    ]
    lineup = setter(assets=assets)

    assert lineup["RB1"] == "player1"
    assert lineup["RB2"] == "player2"

    assert lineup.starter_value == 100
    assert lineup.total_value == 150


def test_lineup_depth2():
    setter = make_lineup_setter(RB=1, depth=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
        Asset(name="player3", pos="RB", value=25),
    ]
    lineup = setter(assets=assets)

    assert lineup["RB1"] == "player1"
    assert lineup["RB2"] == "player2"
    with pytest.raises(KeyError):
        lineup["RB3"]

    assert lineup.starter_value == 100
    assert lineup.total_value == 150


def test_lineup_depth_flex():
    setter = make_lineup_setter(RB=1, FLEX=1, depth=1)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
        Asset(name="player3", pos="WR", value=50),
    ]
    lineup = setter(assets=assets)

    assert lineup["RB1"] == "player1"

    # Flex can take either 2 or 3, since they're equal
    assert (lineup["FLEX1"] == "player2") or (lineup["FLEX1"] == "player3")

    assert lineup.starter_value == 150  # 2 Start
    assert lineup.total_value == 200  # all 3 included in depth


def test_lineup_no_depth_flex():
    setter = make_lineup_setter(RB=1, FLEX=1, depth=0)
    assets = [
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=50),
        Asset(name="player3", pos="WR", value=50),
    ]
    lineup = setter(assets=assets)

    assert lineup["RB1"] == "player1"

    # Flex can take either 2 or 3, since they're equal
    assert (lineup["FLEX1"] == "player2") or (lineup["FLEX1"] == "player3")

    assert lineup.starter_value == 150  # 2 Start
    assert lineup.total_value == 150  # 2 start, no depth


def test_lineup_flex_complex_no_depth():
    setter = make_lineup_setter(QB=1, RB=2, WR=1, TE=1, FLEX=1, depth=0)
    assets = [  # Order by pos for ease on eyes
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=75),
        Asset(name="player5", pos="RB", value=50),
        Asset(name="player3", pos="QB", value=100),
        Asset(name="player4", pos="TE", value=50),
        Asset(name="player8", pos="TE", value=25),
        Asset(name="player6", pos="WR", value=150),
        Asset(name="player7", pos="WR", value=75),
    ]
    lineup = setter(assets)

    # Assert lineup is correct
    assert lineup["QB1"] == "player3"
    assert lineup["RB1"] == "player1"
    assert lineup["RB2"] == "player2"
    assert lineup["WR1"] == "player6"
    assert lineup["TE1"] == "player4"
    assert lineup["FLEX1"] == "player7"

    # Assert values are correct
    assert lineup.starter_value == 550
    assert lineup.total_value == 550


def test_lineup_flex_complex_depth():
    setter = make_lineup_setter(QB=1, RB=2, WR=1, TE=1, FLEX=1, SUPER=1, depth=1)
    assets = [  # Order by pos for ease on eyes
        Asset(name="player3", pos="QB", value=100),
        Asset(name="player9", pos="QB", value=75),
        Asset(name="player1", pos="RB", value=100),
        Asset(name="player2", pos="RB", value=75),
        Asset(name="player5", pos="RB", value=50),
        Asset(name="player4", pos="TE", value=50),
        Asset(name="player8", pos="TE", value=25),
        Asset(name="player6", pos="WR", value=150),
        Asset(name="player7", pos="WR", value=70),
        Asset(name="player10", pos="WR", value=50),
        Asset(name="player11", pos="RB", value=25),
    ]
    lineup = setter(assets)

    # Assert lineup is correct
    assert lineup["QB1"] == "player3"
    assert (
        lineup["QB2"] == "player9"
    ), "If QB2 starts, but they're the only other QB, they're also QB2 as depth in a non starting role"
    assert lineup["RB1"] == "player1"
    assert lineup["RB2"] == "player2"
    assert lineup["WR1"] == "player6"
    # assert lineup["WR2"] == "Player7"
    assert lineup["TE1"] == "player4"
    assert lineup["FLEX1"] == "player7"
    assert lineup["SUPER1"] == "player9"

    assert lineup.starter_value == 620
    assert lineup.total_value == 845


if __name__ == "__main__":
    test_pprint_no_error()
