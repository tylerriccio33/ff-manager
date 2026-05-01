"""Unit tests for ff_manager.league.BaseLeague behavior."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ff_manager.league import PLATFORM_SWITCH, SleeperLeague

DATA_DIR = Path(__file__).parent / "data"


def test_getitem_int_and_str(league_basic):
    by_int = league_basic[0]
    by_name = league_basic[by_int.name]
    assert by_name.name == by_int.name


def test_getitem_invalid_string(league_basic):
    with pytest.raises(ValueError, match="too broad"):
        league_basic["zzz-no-such-team"]


def test_getitem_invalid_type(league_basic):
    with pytest.raises(TypeError, match="integer or a string"):
        league_basic[1.5]


def test_refresh_requires_data_loc():
    with pytest.raises(ValueError, match="data_loc must be provided"):
        SleeperLeague(
            profile={"id": 0, "lineup": {}},
            data_loc=None,  # ty: ignore[invalid-argument-type]
            refresh_data=False,
        )


def test_save_data_list(tmp_path: Path, league_basic):
    out = tmp_path / "out.parquet"
    league_basic.save_data(
        data=[{"id": "1", "team": "t", "name": "n", "pos": "QB", "value": 1}],
        outfile_loc=out,
    )
    assert out.exists()
    assert pq.read_table(out).num_rows == 1


def test_save_data_table(tmp_path: Path, league_basic):
    out = tmp_path / "out.parquet"
    table = pa.table({"a": [1, 2]})
    league_basic.save_data(data=table, outfile_loc=out)
    assert pq.read_table(out).num_rows == 2


def test_platform_switch_keys():
    assert set(PLATFORM_SWITCH) == {"espn", "sleeper"}
