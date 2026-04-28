"""Shared pytest fixtures for the ff-manager test suite."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ff_manager.league import PLATFORM_SWITCH

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def make_league():
    """
    Build a league from a profile + roster fixture pair on disk.

    Returns a callable so tests can pick the fixture pair they want.
    """

    def _build(profile_path: str | Path, players_path: str | Path):
        with Path(profile_path).open() as f:
            profile = yaml.safe_load(f)
        league_cls = PLATFORM_SWITCH[profile["platform"]]
        return league_cls(profile=profile, data_loc=players_path, refresh_data=False)

    return _build


@pytest.fixture
def league_basic(make_league):
    """The canonical 3-team league used by the e2e baseline test."""
    return make_league(
        DATA_DIR / "league_basic.profile.json",
        DATA_DIR / "league_basic.players.json",
    )
