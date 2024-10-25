from __future__ import annotations

import itertools
from collections import UserDict
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from ff_manager.const import FLEX_POS, LINEUP_KEY_SORTER, SPECIALS_SLOTS, SUPER_POS

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ff_manager.model import Asset


class LineupMeta(UserDict):  # Re-patched every time function is called
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._depth: int | None = None
        self._starter_value = None
        self._start_value_set: bool = False
        self._starter_keys: list[str] | None = None
        self._starter_keys_value_set: bool = False

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

    @property
    def total_value(self):
        return sum(getattr(player, "value", 0) for player in self.data.values())

    @property
    def starter_value(self):
        return self._starter_value

    @starter_value.setter
    def starter_value(self, value):
        if self._start_value_set:
            raise AttributeError("Starter value is set upon construction only.")
        self._starter_value = value
        self._start_value_set = True

    @property
    def starter_keys(self) -> list[str]:
        return self._starter_keys

    @starter_keys.setter
    def starter_keys(self, keys: list[str]):
        if self._starter_keys_value_set:
            raise AttributeError("Starter keys is set upon construction only.")
        self._starter_keys = keys
        self._starter_keys_value_set = True

    def pprint(self) -> None:
        vertical_lineup: list[tuple] = []
        for sort_key in LINEUP_KEY_SORTER:
            vertical_lineup.extend(
                sorted(
                    (k[:-1], k, v)
                    for k, v in self.data.items()
                    if k.startswith(sort_key)
                )
            )

        # Make horizontal
        horizontal_lineup: list[list[tuple[str, Asset]]] = [
            [p] for p in vertical_lineup if p[1] in self.starter_keys
        ]
        depth_players = [p for p in vertical_lineup if p[1] not in self.starter_keys]

        for i, starter in enumerate(horizontal_lineup):
            starter_pos_group: str = starter[0][0]
            for depth_player in depth_players:
                if depth_player[0] == starter_pos_group:
                    horizontal_lineup[i].append(depth_player)

        # Build Table:
        max_depth = max(len(slot) for slot in horizontal_lineup)

        table = Table(title="Depth Chart")

        for i in range(max_depth):
            table.add_column(f"Slot{i}", style="cyan", no_wrap=True)
            table.add_column(
                f"Player{i}", style="magenta", no_wrap=True, max_width=1_000
            )

        for slot in horizontal_lineup:
            args = []
            for i in range(max_depth):
                try:
                    args.append(str(slot[i][1]))
                    args.append(str(slot[i][2]))
                except IndexError:  # No player filled for this slot
                    args.append(None)
                    args.append(None)
            table.add_row(*args)

        console = Console()
        console.print(table)

    def __repr__(self):
        raise TypeError("Use .pprint()")


def make_lineup_setter(depth: int = 0, **lineup_template: dict) -> Callable:
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

    def _setter(assets: Sequence[Asset]) -> LineupMeta:
        lineup = LineupMeta()

        lineup._depth = depth

        # Iterate down lineup:
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
            lineup.starter_keys = list(lineup.data.keys())
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
                try:
                    player = next(a for a in avail_players if a.pos == slot)
                except StopIteration:
                    pass
                else:
                    avail_players.remove(player)
                    lineup[slot] = player

            # Iterate down special spots using all players
            avail_players = all_sorted_players.copy()
            special_slots: list[str] = [
                slot for slot in SPECIALS_SLOTS if slot in flat_slots
            ] * depth
            for slot in special_slots:
                try:
                    player = next(a for a in avail_players if a.pos == slot)
                except StopIteration:
                    pass
                else:
                    avail_players.remove(player)
                    lineup[slot] = player

        else:
            lineup.starter_value = sum(
                getattr(player, "value", 0) for player in lineup.data.values()
            )
            lineup.starter_keys = list(lineup.data.keys())

        return lineup

    return _setter
