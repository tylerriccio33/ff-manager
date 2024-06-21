from __future__ import annotations

from enum import Enum
from functools import cache
from itertools import chain

# ! slot and Lineup should probably be merged


class LineupSlots(Enum):
    """slots in a lineup"""

    # ! why can't I overload the typed dict's repr; use dict for now
    QB1 = 1
    RB1 = 2
    RB2 = 3
    WR1 = 4
    WR2 = 5
    TE1 = 6
    FLEX1 = 7
    FLEX2 = 8
    SUPER1 = 9

    def __repr__(self) -> str:
        return "\n\t\t\t\t\t\t\t\t\t".join(
            f"{slot}: {asset}" for slot, asset in self.items()
        )

    @classmethod
    def build_lineup_from_slots(cls) -> dict:
        return {slot: None for slot in cls.__members__}


class Role(Enum):
    """roles can play slots; valid slots are returned"""

    QB = (LineupSlots.QB1,)
    RB = (
        LineupSlots.RB1,
        LineupSlots.RB2,
    )
    WR = (
        LineupSlots.WR1,
        LineupSlots.WR2,
    )
    TE = (LineupSlots.TE1,)
    FLEX = (
        LineupSlots.FLEX1,
        LineupSlots.FLEX2,
    )
    SUPER = (LineupSlots.SUPER1,)

    @classmethod
    @cache
    def unpack_roles(cls) -> list[tuple[Role, tuple[LineupSlots, ...]]]:
        return [(role, slot) for role in cls for slot in role.value]

    @classmethod
    def unpack_slots(cls) -> list[LineupSlots]:
        return [slot for role in cls for slot in role.value]


class Pos(Enum):
    """positions can play roles; valid roles are returned"""

    QB = (Role.QB, Role.SUPER)
    RB = (Role.RB, Role.FLEX, Role.SUPER)
    WR = (Role.WR, Role.FLEX, Role.SUPER)
    TE = (Role.TE, Role.FLEX, Role.SUPER)

    def __contains__(self, string) -> bool:
        return any(string in values for values in self.value)

    @classmethod
    def get_pct_lineup_fillable(cls, pos: Pos):
        return len(cls[pos].value) / len(LineupSlots)

    @classmethod
    def get_available_slots(cls, pos: Pos) -> list[LineupSlots]:
        """get available slots for position"""
        slots = [role.value for role in pos.value]
        return list(chain(*slots))

    # TODO: add custom error for invalid positions
    # TODO: return a tuple of slots instead
