from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from ff_manager.const import FLEX_POS, LINEUP_KEY_SORTER, SUPER_POS

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ff_manager.model import Asset


def _eligible_for(slot: str) -> tuple[str, ...]:
    if slot == "FLEX":
        return FLEX_POS
    if slot in ("SUPER", "SUPERFLEX"):
        return SUPER_POS
    return (slot,)


@dataclass(frozen=True)
class FilledSlot:
    label: str
    slot: str
    eligible: tuple[str, ...]
    player: Asset | None
    weight: float

    @property
    def is_starter(self) -> bool:
        return self.weight == 1.0


class LineupMeta:
    def __init__(self, slots: list[FilledSlot], starter_count: int):
        self.slots = slots
        self.starter_count = starter_count

    @property
    def starter_value(self) -> float:
        return sum(
            s.player.value
            for s in self.slots[: self.starter_count]
            if s.player is not None
        )

    @property
    def total_value(self) -> float:
        return sum(
            s.player.value * s.weight for s in self.slots if s.player is not None
        )

    def __getitem__(self, label: str) -> Asset | None:
        for s in self.slots:
            if s.label == label:
                return s.player
        raise KeyError(label)

    def __contains__(self, label: object) -> bool:
        return any(s.label == label for s in self.slots)

    def __repr__(self) -> str:
        n_filled = sum(1 for s in self.slots if s.player is not None)
        return (
            f"<Lineup starters={self.starter_count} "
            f"filled={n_filled}/{len(self.slots)} "
            f"starter_value={self.starter_value:.0f} "
            f"total_value={self.total_value:.1f}>"
        )


def render_table(meta: LineupMeta | None) -> str:
    """Rich-formatted table view of a lineup. Use this instead of repr for display."""
    if meta is None:
        return ""
    starter_labels = {
        s.label for s in meta.slots[: meta.starter_count] if s.player is not None
    }

    vertical: list[tuple[str, str, Asset]] = []
    for sort_key in LINEUP_KEY_SORTER:
        vertical.extend(
            sorted(
                (s.slot, s.label, s.player)
                for s in meta.slots
                if s.player is not None and s.slot == sort_key
            )
        )

    horizontal: list[list[tuple[str, str, Asset]]] = [
        [p] for p in vertical if p[1] in starter_labels
    ]
    depth_rows = [p for p in vertical if p[1] not in starter_labels]
    for i, starter in enumerate(horizontal):
        starter_pos = starter[0][0]
        for d in depth_rows:
            if d[0] == starter_pos:
                horizontal[i].append(d)

    if not horizontal:
        return ""

    max_depth = max(len(slot) for slot in horizontal)
    table = Table()
    for i in range(max_depth):
        table.add_column(f"Slot{i}", style="cyan", no_wrap=True)
        table.add_column(f"Player{i}", style="magenta", no_wrap=True, max_width=1_000)

    for slot in horizontal:
        args: list[str | None] = []
        for i in range(max_depth):
            if i < len(slot):
                args.append(str(slot[i][1]))
                args.append(str(slot[i][2]))
            else:
                args.append(None)
                args.append(None)
        table.add_row(*args)

    console = Console()
    with console.capture() as capture:
        console.print(table)
    return capture.get()


def make_lineup_setter(
    *,
    depth: int = 0,
    depth_weights: Sequence[float] | None = None,
    **lineup_template: int,
) -> Callable[[Sequence[Asset]], LineupMeta]:
    if depth_weights is None:
        depth_weights = [0.5 ** (i + 1) for i in range(depth)]
    elif len(depth_weights) != depth:
        raise ValueError(
            f"depth_weights length {len(depth_weights)} does not match depth {depth}"
        )

    starter_specs: list[tuple[str, tuple[str, ...]]] = []
    for slot, n in lineup_template.items():
        eligible = _eligible_for(slot)
        starter_specs.extend([(slot, eligible)] * n)

    counts_per_layer: Counter[str] = Counter(slot for slot, _ in starter_specs)
    unique_slots = list(dict.fromkeys(slot for slot, _ in starter_specs))

    def _setter(assets: Sequence[Asset]) -> LineupMeta:
        sorted_players = sorted(assets, key=lambda a: a.value, reverse=True)

        # --- Starter pass: greedy across all slot types, players removed once taken ---
        starter_avail = sorted_players.copy()
        starter_results: list[tuple[str, tuple[str, ...], Asset | None]] = []
        for slot, eligible in starter_specs:
            player = next((a for a in starter_avail if a.pos in eligible), None)
            if player is not None:
                starter_avail.remove(player)
            starter_results.append((slot, eligible, player))

        starter_ids = {id(p) for _, _, p in starter_results if p is not None}
        bench_pool = [a for a in sorted_players if id(a) not in starter_ids]

        # Depth: per-slot pool. Same bench player can fill multiple slot TYPES,
        # but is consumed across layers and within-layer occurrences of the same slot.
        slot_picks: dict[str, list[Asset | None]] = {}
        for slot in unique_slots:
            eligible = _eligible_for(slot)
            avail = [a for a in bench_pool if a.pos in eligible]
            n_picks = counts_per_layer[slot] * depth
            picks: list[Asset | None] = []
            for _ in range(n_picks):
                picks.append(avail.pop(0) if avail else None)
            slot_picks[slot] = picks

        # Materialize: starters first, then layer-major x template-order depth
        all_filled: list[tuple[str, tuple[str, ...], Asset | None, float]] = [
            (s, e, p, 1.0) for s, e, p in starter_results
        ]
        pick_idx: dict[str, int] = dict.fromkeys(unique_slots, 0)
        for layer_idx in range(depth):
            weight = depth_weights[layer_idx]
            for slot, eligible in starter_specs:
                i = pick_idx[slot]
                player = slot_picks[slot][i]
                pick_idx[slot] = i + 1
                all_filled.append((slot, eligible, player, weight))

        slots: list[FilledSlot] = []
        counters: dict[str, int] = {}
        for slot, eligible, player, weight in all_filled:
            n = counters.get(slot, 0) + 1
            counters[slot] = n
            slots.append(
                FilledSlot(
                    label=f"{slot}{n}",
                    slot=slot,
                    eligible=eligible,
                    player=player,
                    weight=weight,
                )
            )

        return LineupMeta(slots=slots, starter_count=len(starter_results))

    return _setter
