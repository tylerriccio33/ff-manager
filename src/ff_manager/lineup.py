from __future__ import annotations

import itertools
from collections import Counter, UserDict
from typing import TYPE_CHECKING

from ff_manager.const import FLEX_POS, SPECIALS_SLOTS, SUPER_POS

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ff_manager.model import Asset


def make_lineup_setter(depth: int = 0, **lineup_template: dict) -> Callable:
    class LineupMeta(UserDict):  # Re-patched every time function is called
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._starter_value = None
            self._start_value_set = False
            self._depth: int | None = None

        def __setitem__(self, key, value):
            # Check if the key already exists
            original_key = key
            counter = 1
            key = f"{original_key}1"
            while key in self.data:
                key = f"{original_key}{counter}"
                counter += 1

            # Set the value for the appropriate key
            self.data[key] = value

        # TODO: remove this upon lineup value refactoring
        # ? cache this; only needs to get computed once
        def pos_slots_fillable(self, pos: str) -> float:
            return self._pos_count_lookup[pos] / len(self)

        @property
        def total_value(self):
            return sum(player.value for player in self.data.values())

        @property
        def starter_value(self):
            return self._starter_value

        @starter_value.setter
        def starter_value(self, value):
            if self._start_value_set:
                raise AttributeError("Starter value is set upon construction only.")
            self._starter_value = value
            self._start_value_set = True

        def __repr__(self):
            return "\n\t\t\t\t\t".join(f"{k}: {v}" for k, v in self.data.items())

    nested_slots = [[slot] * n for slot, n in lineup_template.items()]
    flat_slots = tuple(itertools.chain.from_iterable(nested_slots))

    # Renest but replace super and flex
    fillable_slots = []
    for slot in flat_slots:
        if slot == "FLEX":
            cur_slot = FLEX_POS
        elif slot in ("SUPERFLEX", "SUPER"):
            cur_slot = SUPER_POS
        else:
            cur_slot = (slot,)
        fillable_slots.append(cur_slot)

    # Patch LineupMeta class
    counts: Counter = Counter(pos for sublist in fillable_slots for pos in sublist)
    LineupMeta._pos_count_lookup = counts

    def _setter(assets: Sequence[Asset]) -> LineupMeta:
        # iterate down lineup selecting eligable players

        lineup = LineupMeta()

        # Asset must have a `value` attribute
        all_sorted_players = sorted(assets, key=lambda a: a.value, reverse=True)
        avail_players = all_sorted_players.copy()

        for slot, fillable_slot in zip(flat_slots, fillable_slots, strict=True):
            try:
                player = next(a for a in avail_players if a.pos in fillable_slot)
                avail_players.remove(player)
            except StopIteration:  # No available players fill this position
                player = None
            lineup[slot] = player

        if depth:
            lineup.starter_value = sum(player.value for player in lineup.data.values())

            # Iterate down regular spots using available players:
            regular_slots: list[str] = [
                slot for slot in flat_slots if slot not in SPECIALS_SLOTS
            ] * depth
            rm_these_players = [
                slot
                for slot in lineup.data
                if any(
                    slot.startswith(special_slot[:-1])
                    for special_slot in SPECIALS_SLOTS
                )
            ]
            players_in_special_slots = [
                player
                for slot, player in lineup.data.items()
                if slot in rm_these_players
            ]
            avail_players += players_in_special_slots

            for slot in regular_slots:
                print(f"Trying to fill {slot}")
                try:
                    player = next(a for a in avail_players if a.pos == slot)
                    avail_players.remove(player)
                    lineup[slot] = player
                    print(f"Filled {slot} with {player}")
                except StopIteration:
                    pass

            # Iterate down special spots using all players
            avail_players = all_sorted_players.copy()
            special_slots: list[str] = [
                slot for slot in SPECIALS_SLOTS if slot in flat_slots
            ] * depth
            for slot in special_slots:
                print(f"Trying to fill {slot}")
                try:
                    player = next(a for a in avail_players if a.pos == slot)
                    avail_players.remove(player)
                    lineup[slot] = player
                    print(f"Filled {slot} with {player}")
                except StopIteration:
                    pass

        else:
            lineup.starter_value = sum(
                getattr(player, "value", 0) for player in lineup.data.values()
            )

        return lineup

    return _setter
