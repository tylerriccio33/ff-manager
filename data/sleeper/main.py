from __future__ import annotations

from sleeper.api import LeagueAPIClient
from itertools import chain
from sleeper.model import (
    Roster,
)
import requests

LEAGUE_ID = "1049399476387028992"


league_rosters: list[Roster] = LeagueAPIClient.get_rosters(league_id=LEAGUE_ID)
all_player_ids = set(chain(*[r.players for r in league_rosters]))

# ! Request this sparingly
player_res = requests.get("https://api.sleeper.app/v1/players/nfl")
players = player_res.json()

# Filter Players:
valid_players = {pid: data for pid, data in players.items() if pid in all_player_ids}

# Clean Up:
processed_players = []
for pid, player in valid_players.items():
    new_player = {
        "id": pid,
        "name": player["first_name"] + player["last_name"],
        "pos": player["position"],
        "fp_id": player["fantasy_data_id"], # ! this might be wrong
        "starter_value": 
    }
    

players["1150"]

# Save JSON:
	{
		"team": "T Law and Order",
		"id": "10219",
		"name": "Chris Rodriguez",
		"pos": "RB",
		"fp_id": "22986",
		"dynasty_value": 25,
		"starter_value": 0.6
	},