from __future__ import annotations

import itertools
from collections import Counter, UserDict
from typing import TYPE_CHECKING

from ff_manager.const import FLEX_POS, SUPER_POS

if TYPE_CHECKING:
    from collections.abc import Callable


def make_lineup_setter(profile: dict) -> Callable:
    template: dict[str, int] = profile["lineup"]

    class LineupMeta(UserDict):
        def __setitem__(self, key, value):
            # Check if the key already exists
            original_key = key
            counter = 1
            while key in self.data:
                key = f"{original_key}{counter}"
                counter += 1
            # Set the value for the appropriate key
            self.data[key] = value

        # ? cache this; only needs to get computed once
        def pos_slots_fillable(self, pos: str) -> float:
            return self._pos_count_lookup[pos] / len(self)

        def __repr__(self):
            return "\n\t\t\t\t\t".join(f"{k}: {v}" for k, v in self.data.items())

    nested_slots = [[slot] * n for slot, n in template.items()]
    flat_slots = tuple(itertools.chain.from_iterable(nested_slots))

    # Renest but replace super and flex
    with_subroles = []
    for slot in flat_slots:
        if slot == "FLEX":
            cur_slot = FLEX_POS
        elif slot in ("SUPERFLEX", "SUPER"):
            cur_slot = SUPER_POS
        else:
            cur_slot = (slot,)
        with_subroles.append(cur_slot)

    # Patch LineupMeta class
    counts: Counter = Counter(pos for sublist in with_subroles for pos in sublist)
    LineupMeta._pos_count_lookup = counts

    def _setter(sorted_assets) -> LineupMeta:
        # iterate down lineup selecting eligable players

        lineup = LineupMeta()
        avail_players = sorted_assets.copy()

        for slot, subroles in zip(flat_slots, with_subroles, strict=True):
            try:
                player = next(a for a in avail_players if a.pos in subroles)
                avail_players.remove(player)
            except StopIteration:  # Lineup does not have this position
                player = None
            lineup[slot] = player

        return lineup

    return _setter
