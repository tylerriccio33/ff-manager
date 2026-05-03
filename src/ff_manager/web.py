"""
Barebones Flask web layer for ff-manager.

Mirrors the CLI's `find-trades` inputs as an HTML form. Uses the
checked-in sleeper test fixtures as a stand-in "database" so the page
works out of the box.

Run with:
    uv run python -m ff_manager.web
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template_string, request

from ff_manager.api import eval_trades
from ff_manager.league import PLATFORM_SWITCH

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "tests" / "data"
DB_DIR = REPO_ROOT / "db"

# Fixture-backed "leagues" — each entry is a (profile, players) pair.
EXAMPLES: dict[str, tuple[Path, Path]] = {
    "basic (3-team sleeper)": (
        DATA_DIR / "league_basic.profile.json",
        DATA_DIR / "league_basic.players.json",
    ),
    "10-team sleeper": (
        DATA_DIR / "league_10team.profile.json",
        DATA_DIR / "league_10team.players.json",
    ),
}

# Real-league snapshots downloaded into db/ (gitignored). Only shown when present.
_DB_EXAMPLES: dict[str, tuple[Path, Path]] = {
    "tyler dynasty (real sleeper)": (
        DB_DIR / "tyler_dynasty_sleeper.profile.json",
        DB_DIR / "tyler_dynasty_sleeper.parquet",
    ),
}
for _label, (_prof, _data) in _DB_EXAMPLES.items():
    if _prof.exists() and _data.exists():
        EXAMPLES[_label] = (_prof, _data)


def _build_league(example_key: str):
    profile_path, players_path = EXAMPLES[example_key]
    import yaml

    with profile_path.open() as f:
        profile = yaml.safe_load(f)
    cls = PLATFORM_SWITCH[profile["platform"]]
    return cls(profile=profile, data_loc=players_path, refresh_data=False)


PAGE = """
<!doctype html>
<title>ff-manager</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 820px; margin: 2rem auto; }
  label { display: block; margin: 0.4rem 0 0.1rem; font-weight: 600; }
  input, select { width: 100%; padding: 0.3rem; }
  .row { display: flex; gap: 1rem; }
  .row > div { flex: 1; }
  pre { background: #f4f4f4; padding: 1rem; overflow-x: auto; }
  .err { color: #b00; }
</style>
<h1>ff-manager — find trades</h1>
<form method="post">
  <label>Example league</label>
  <select name="example">
    {% for k in examples %}
      <option value="{{k}}" {% if k == form.example %}selected{% endif %}>{{k}}</option>
    {% endfor %}
  </select>

  <label>Team (your team)</label>
  <input name="team" value="{{ form.team or 'team1' }}" required>

  <div class="row">
    <div>
      <label>max_fleece</label>
      <input name="max_fleece" type="number" value="{{ form.max_fleece or 20 }}">
    </div>
    <div>
      <label>max_assets</label>
      <input name="max_assets" type="number" value="{{ form.max_assets or 1 }}">
    </div>
    <div>
      <label>min_asset_value</label>
      <input name="min_asset_value" type="number" value="{{ form.min_asset_value or 40 }}">
    </div>
  </div>

  <label>target_pos (comma separated, e.g. RB,WR)</label>
  <input name="target_pos" value="{{ form.target_pos or '' }}">

  <label>assets_from_team</label>
  <input name="assets_from_team" value="{{ form.assets_from_team or '' }}">

  <label>assets_not_from_team</label>
  <input name="assets_not_from_team" value="{{ form.assets_not_from_team or '' }}">

  <label>return_contains (comma separated player names)</label>
  <input name="return_contains" value="{{ form.return_contains or '' }}">

  <p><button type="submit">Find trades</button></p>
</form>

{% if error %}<p class="err">{{ error }}</p>{% endif %}

{% if trades is not none %}
  <h2>Results ({{ trades|length }})</h2>
  {% for t in trades %}<pre>{{ t }}</pre>{% endfor %}
{% endif %}
"""


def _csv(s: str) -> tuple[str, ...] | None:
    s = (s or "").strip()
    if not s:
        return None
    return tuple(p.strip() for p in s.split(",") if p.strip())


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        form: dict = {}
        trades = None
        error = None

        if request.method == "POST":
            form = request.form.to_dict()
            try:
                reqs: dict = {
                    "team": form["team"],
                    "max_fleece": int(form.get("max_fleece") or 20),
                    "max_assets": int(form.get("max_assets") or 1),
                }
                if form.get("min_asset_value"):
                    reqs["min_asset_value"] = int(form["min_asset_value"])
                for key in (
                    "target_pos",
                    "assets_from_team",
                    "assets_not_from_team",
                    "return_contains",
                ):
                    val = _csv(form.get(key, ""))
                    if val is not None:
                        reqs[key] = val

                league = _build_league(form.get("example") or next(iter(EXAMPLES)))
                trades = eval_trades(league=league, reqs=reqs)
            except Exception as e:
                error = f"{type(e).__name__}: {e}"

        return render_template_string(
            PAGE, examples=list(EXAMPLES), form=form, trades=trades, error=error
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5050)
