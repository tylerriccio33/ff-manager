"""Download Tyler's dynasty Sleeper league into db/ as a parquet snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import requests

from ff_manager.league import SleeperLeague

LEAGUE_ID = "1312110613232640000"
REPO_ROOT = Path(__file__).resolve().parents[1]
NAME = "tyler_dynasty_sleeper"
OUT_PATH = REPO_ROOT / "db" / f"{NAME}.parquet"
PROFILE_PATH = REPO_ROOT / "db" / f"{NAME}.profile.json"

# Sleeper roster slot codes that map to our lineup keys.
SLOT_MAP = {
    "QB": "QB",
    "RB": "RB",
    "WR": "WR",
    "TE": "TE",
    "FLEX": "FLEX",
    "SUPER_FLEX": "SUPER_FLEX",
    "REC_FLEX": "FLEX",
    "WRRB_FLEX": "FLEX",
}


def fetch_lineup(league_id: str) -> dict[str, int]:
    resp = requests.get(f"https://api.sleeper.app/v1/league/{league_id}")
    resp.raise_for_status()
    positions: list[str] = json.loads(resp.content)["roster_positions"]
    lineup: dict[str, int] = {}
    for slot in positions:
        key = SLOT_MAP.get(slot)
        if key is None:
            continue
        lineup[key] = lineup.get(key, 0) + 1
    return lineup


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "platform": "sleeper",
        "id": LEAGUE_ID,
        "lineup": fetch_lineup(LEAGUE_ID),
    }
    print(f"Lineup: {profile['lineup']}")
    SleeperLeague(profile=profile, data_loc=OUT_PATH, refresh_data=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2))
    print(f"Wrote {OUT_PATH} and {PROFILE_PATH}")


if __name__ == "__main__":
    main()
