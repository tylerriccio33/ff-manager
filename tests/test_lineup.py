import pytest

from ff_manager.lineup import make_lineup_setter, render_table
from ff_manager.model import Asset


def test_no_depth_simple():
    setter = make_lineup_setter(RB=1)
    assets = [
        Asset(name="p1", pos="RB", value=100),
        Asset(name="p2", pos="RB", value=50),
    ]
    lineup = setter(assets)

    assert lineup["RB1"] == "p1"
    assert lineup.starter_value == 100
    assert lineup.total_value == 100


def test_no_depth_flex_picks_best_eligible():
    setter = make_lineup_setter(RB=1, FLEX=1)
    assets = [
        Asset(name="p1", pos="RB", value=100),
        Asset(name="p2", pos="RB", value=50),
    ]
    lineup = setter(assets)

    assert lineup["RB1"] == "p1"
    assert lineup["FLEX1"] == "p2"
    assert lineup.starter_value == 150
    assert lineup.total_value == 150


def test_starter_pass_no_double_count():
    """A starter never gets re-counted as depth."""
    setter = make_lineup_setter(QB=1, RB=1, FLEX=1, depth=1)
    assets = [
        Asset(name="qb", pos="QB", value=100),
        Asset(name="rb1", pos="RB", value=100),
        Asset(name="rb2", pos="RB", value=50),
    ]
    lineup = setter(assets)

    # All 3 players start (rb2 fills FLEX). Bench is empty → all depth slots None.
    assert lineup["QB1"] == "qb"
    assert lineup["RB1"] == "rb1"
    assert lineup["FLEX1"] == "rb2"
    assert lineup["QB2"] is None
    assert lineup["RB2"] is None
    assert lineup["FLEX2"] is None

    assert lineup.starter_value == 250
    assert lineup.total_value == 250  # no double count


def test_bench_player_fans_out_across_slot_types():
    """A single bench WR fills both WR-depth and FLEX-depth slots."""
    setter = make_lineup_setter(WR=1, FLEX=1, depth=1)
    assets = [
        Asset(name="wr1", pos="WR", value=100),
        Asset(name="wr2", pos="WR", value=80),
        Asset(name="wr3", pos="WR", value=50),
    ]
    lineup = setter(assets)

    assert lineup["WR1"] == "wr1"
    assert lineup["FLEX1"] == "wr2"
    # wr3 is the only bench player. He fills both depth slots.
    assert lineup["WR2"] == "wr3"
    assert lineup["FLEX2"] == "wr3"

    assert lineup.starter_value == 180
    assert lineup.total_value == 180 + 0.5 * 50 + 0.5 * 50  # 230


def test_within_slot_unique_across_layers():
    """Across depth layers, the same slot type draws progressively (WR2 ≠ WR3)."""
    setter = make_lineup_setter(WR=1, depth=2)
    assets = [
        Asset(name="wr1", pos="WR", value=100),
        Asset(name="wr2", pos="WR", value=80),
        Asset(name="wr3", pos="WR", value=50),
        Asset(name="wr4", pos="WR", value=25),
    ]
    lineup = setter(assets)

    assert lineup["WR1"] == "wr1"
    assert lineup["WR2"] == "wr2"  # layer 0
    assert lineup["WR3"] == "wr3"  # layer 1

    assert lineup.starter_value == 100
    assert lineup.total_value == 100 + 0.5 * 80 + 0.25 * 50  # 152.5


def test_within_layer_repeated_slot_type_unique():
    """RB1, RB2 starters; RB3, RB4 in one layer must be distinct bench players."""
    setter = make_lineup_setter(RB=2, depth=1)
    assets = [
        Asset(name="rb1", pos="RB", value=100),
        Asset(name="rb2", pos="RB", value=75),
        Asset(name="rb3", pos="RB", value=50),
        Asset(name="rb4", pos="RB", value=25),
    ]
    lineup = setter(assets)

    assert lineup["RB1"] == "rb1"
    assert lineup["RB2"] == "rb2"
    assert lineup["RB3"] == "rb3"
    assert lineup["RB4"] == "rb4"

    assert lineup.starter_value == 175
    assert lineup.total_value == 175 + 0.5 * 50 + 0.5 * 25  # 212.5


def test_geometric_default_decay():
    setter = make_lineup_setter(RB=1, depth=3)
    assets = [
        Asset(name=f"p{i}", pos="RB", value=v)
        for i, v in enumerate([100, 80, 60, 40], start=1)
    ]
    lineup = setter(assets)

    # 100 + 0.5*80 + 0.25*60 + 0.125*40 = 100 + 40 + 15 + 5 = 160
    assert lineup.total_value == 160


def test_explicit_depth_weights():
    setter = make_lineup_setter(RB=1, depth=2, depth_weights=[0.8, 0.4])
    assets = [
        Asset(name="p1", pos="RB", value=100),
        Asset(name="p2", pos="RB", value=50),
        Asset(name="p3", pos="RB", value=25),
    ]
    lineup = setter(assets)

    # 100 + 0.8*50 + 0.4*25 = 100 + 40 + 10 = 150
    assert lineup.total_value == 150


def test_depth_weights_length_mismatch_raises():
    with pytest.raises(ValueError, match="depth_weights"):
        make_lineup_setter(RB=1, depth=2, depth_weights=[0.5])


def test_complex_no_depth():
    setter = make_lineup_setter(QB=1, RB=2, WR=1, TE=1, FLEX=1, depth=0)
    assets = [
        Asset(name="p1", pos="RB", value=100),
        Asset(name="p2", pos="RB", value=75),
        Asset(name="p5", pos="RB", value=50),
        Asset(name="p3", pos="QB", value=100),
        Asset(name="p4", pos="TE", value=50),
        Asset(name="p8", pos="TE", value=25),
        Asset(name="p6", pos="WR", value=150),
        Asset(name="p7", pos="WR", value=75),
    ]
    lineup = setter(assets)

    assert lineup["QB1"] == "p3"
    assert lineup["RB1"] == "p1"
    assert lineup["RB2"] == "p2"
    assert lineup["WR1"] == "p6"
    assert lineup["TE1"] == "p4"
    assert lineup["FLEX1"] == "p7"

    assert lineup.starter_value == 550
    assert lineup.total_value == 550


def test_complex_with_flex_super_depth():
    """End-to-end: FLEX2 and SUPER2 actually get filled (regression for old bug)."""
    setter = make_lineup_setter(QB=1, RB=2, WR=1, TE=1, FLEX=1, SUPER=1, depth=1)
    assets = [
        Asset(name="p3", pos="QB", value=100),
        Asset(name="p9", pos="QB", value=75),
        Asset(name="p1", pos="RB", value=100),
        Asset(name="p2", pos="RB", value=75),
        Asset(name="p5", pos="RB", value=50),
        Asset(name="p4", pos="TE", value=50),
        Asset(name="p8", pos="TE", value=25),
        Asset(name="p6", pos="WR", value=150),
        Asset(name="p7", pos="WR", value=70),
        Asset(name="p10", pos="WR", value=50),
        Asset(name="p11", pos="RB", value=25),
    ]
    lineup = setter(assets)

    # Starters
    assert lineup["QB1"] == "p3"
    assert lineup["RB1"] == "p1"
    assert lineup["RB2"] == "p2"
    assert lineup["WR1"] == "p6"
    assert lineup["TE1"] == "p4"
    assert lineup["FLEX1"] == "p7"
    assert lineup["SUPER1"] == "p9"
    assert lineup.starter_value == 620

    # Depth slots all reachable (no dead code)
    assert lineup["QB2"] is None  # no bench QB
    assert lineup["RB3"] == "p5"
    assert lineup["RB4"] == "p11"
    assert lineup["WR2"] == "p10"
    assert lineup["TE2"] == "p8"
    assert lineup["FLEX2"] == "p5"  # bench RB, also fills RB-depth
    assert lineup["SUPER2"] == "p5"

    # 620 + 0.5 * (50 + 25 + 50 + 25 + 50 + 50) = 620 + 125
    assert lineup.total_value == 745


def test_repr_is_cheap():
    """__repr__ shouldn't render the rich table."""
    setter = make_lineup_setter(RB=1, depth=1)
    lineup = setter([Asset(name="p1", pos="RB", value=100)])
    r = repr(lineup)
    assert "<Lineup" in r
    assert "starter_value" in r


def test_render_table_no_error():
    setter = make_lineup_setter(QB=1, RB=2, FLEX=1, depth=2)
    assets = [
        Asset(name="p1", pos="RB", value=100),
        Asset(name="p2", pos="RB", value=50),
        Asset(name="p3", pos="QB", value=80),
        Asset(name="p4", pos="WR", value=40),
    ]
    lineup = setter(assets)
    out = render_table(lineup)
    assert isinstance(out, str)


def test_missing_slot_keyerror():
    setter = make_lineup_setter(RB=1)
    lineup = setter([Asset(name="p1", pos="RB", value=100)])
    with pytest.raises(KeyError):
        lineup["RB2"]
