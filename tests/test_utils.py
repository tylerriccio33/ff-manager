"""Unit tests for ff_manager.utils."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from ff_manager.model import Asset
from ff_manager.utils import (
    containerize_str,
    diff_assets,
    hierarchical_data_load,
    ingest_reqs,
    sink_repr,
)


def test_hierarchical_data_load_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        hierarchical_data_load(tmp_path / "does-not-exist.parquet")


def test_containerize_str_variants():
    assert containerize_str(None) is None
    assert containerize_str("a") == ("a",)
    assert containerize_str(["a", "b"]) == ("a", "b")


def test_diff_assets():
    a, b, c = Asset(name="a"), Asset(name="b"), Asset(name="c")
    assert diff_assets([a, b, c], [b]) == (a, c)


def test_ingest_reqs_missing_required():
    with pytest.raises(ValueError, match="must be in the reqs"):
        ingest_reqs({})


def test_ingest_reqs_replaces_dashes():
    out = ingest_reqs({"team": "t1", "max-fleece": 10})
    assert out == {"team": "t1", "max_fleece": 10}


def test_sink_repr_writes_file(tmp_path: Path):
    out = tmp_path / "out.txt"
    sink_repr(["x", "y", "z"], out)
    assert out.read_text().splitlines() == ["x", "y", "z"]
