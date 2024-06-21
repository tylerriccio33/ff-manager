"""get all draft picks"""

from __future__ import annotations

import subprocess

import pandas as pd

if __name__ == "__main__":
    SEASON = 2024
    draft_table = pd.read_excel("data/sleeper/draft_table.xlsx")
    draft_table.columns = ("team", "asset")

    def parse_asset(asset: str) -> str:
        try:
            return asset.split(" - ")[1].split(" ")[0]
        except IndexError as ie:
            raise ValueError(f"WARNING: Could not parse {asset}") from ie  # noqa: TRY003

    draft_table["raw_pick"] = draft_table["asset"].apply(parse_asset)

    draft_table[["round", "pick"]] = draft_table["raw_pick"].str.split(".", expand=True)

    draft_table["round"] = draft_table["round"].astype(int)
    draft_table["pick"] = draft_table["pick"].astype(int)

    draft_table = draft_table.sort_values(by=["round", "pick"])

    draft_table["pick_number"] = range(len(draft_table))
    draft_table["pick_number"] = draft_table["pick_number"] + 1

    # Get Values:
    # TODO: add refresh option
    fpath = "data/sleeper/get_pick_values.R"
    subprocess.run(
        ["Rscript", fpath],
        capture_output=True,
        check=True,
        text=True,
    )
    all_values = pd.read_csv("data/sleeper/draft_values.csv")
    draft_values = all_values[all_values["player"].str.startswith(str(SEASON))]

    draft_values["player"] = draft_values["player"].str[-4:]
    draft_values = draft_values.rename(columns={"player": "pick"})

    draft_values[["round", "pick"]] = draft_values["pick"].str.split(".", expand=True)

    draft_values["round"] = draft_values["round"].astype(int)
    draft_values["pick"] = draft_values["pick"].astype(int)

    draft_values = draft_values.sort_values(by=["round", "pick"])

    draft_values["pick_number"] = range(len(draft_values))
    draft_values["pick_number"] = draft_values["pick_number"] + 1

    draft_values = draft_values[["pick_number", "value_2qb"]]

    # Merge Back:
    draft_table = draft_table[["team", "pick_number", "round", "pick"]].merge(
        right=draft_values,
        on="pick_number",
    )

    # Write:
    draft_table.to_csv("data/sleeper/draft_table_appended.csv")
