from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ff_manager.const import REQUIRED_REQ_FIELDS

if TYPE_CHECKING:
    from collections.abc import Container


def containerize_str(val: str | Container[str]) -> Container[str]:
    if isinstance(val, str):
        return (val,)
    return val


def ingest_reqs(reqs: dict) -> dict:
    for field in REQUIRED_REQ_FIELDS:
        if field not in reqs:
            raise ValueError(f"The key {field} must be in the reqs.")

    return {k.replace("-", "_"): v for k, v in reqs.items()}


def _correct_fuzzy_team_names(invalid_names: set, valid_names: set) -> dict:
    # TODO: replace this w/string match

    invalid_names_list = list(invalid_names)
    valid_names_list = list(valid_names)

    def _cleaner(val: str) -> str:
        new_val = re.sub(r"<[^>]*>", "", val)
        return " ".join(new_val.split())

    def _cleaner2(val: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", val)

    clean_valids = [_cleaner(valid_name) for valid_name in valid_names_list]

    name_map = {}
    # TODO: replace with contextlib
    for name in invalid_names_list:
        try:
            valid_name_i = valid_names_list.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            valid_name_i = clean_valids.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            clean_name = _cleaner(name)
            valid_name_i = clean_valids.index(clean_name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            cleaner_valids = [_cleaner2(valid_name) for valid_name in clean_valids]
            valid_name_i = cleaner_valids.index(name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass
        try:
            cleaner_name = _cleaner2(name)
            valid_name_i = cleaner_valids.index(cleaner_name)
            name_map[name] = valid_names_list[valid_name_i]
            continue
        except ValueError:
            pass

        raise ValueError(f"Could not map {name}")

    return name_map
