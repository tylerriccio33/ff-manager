"""Fixtures for benchmark suite (run via `make bench`)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ff_manager.league import PLATFORM_SWITCH

DATA_DIR = Path(__file__).parent.parent / "tests" / "data"


def _build(profile_path: Path, players_path: Path):
    with profile_path.open() as f:
        profile = yaml.safe_load(f)
    league_cls = PLATFORM_SWITCH[profile["platform"]]
    return league_cls(profile=profile, data_loc=players_path, refresh_data=False)


@pytest.fixture(scope="session")
def league_10team():
    return _build(
        DATA_DIR / "league_10team.profile.json",
        DATA_DIR / "league_10team.players.json",
    )


@pytest.fixture(scope="session")
def league_basic():
    return _build(
        DATA_DIR / "league_basic.profile.json",
        DATA_DIR / "league_basic.players.json",
    )
