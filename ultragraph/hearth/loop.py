"""Breath loop: fetch -> route -> append -> observe, one tear at a time.

``hearth`` is a thin driver over a :class:`Breath`, which owns one
``SpacetimeGraph``.  Each non-empty tear appends exactly ``BLOCK`` nodes, seeds
only that block, ticks the world once, and collapses an observer value.  The
world is never rewritten or evicted; fingerprints record the growing state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..zerocpu.fixed import ONE
from ..zerocpu.hope import observer, signal
from ..zerocpu.spacetime import SpacetimeGraph
from .block import seed_block
from .kernel import BLOCK, caveman
from .ledger import FokenLedger
from .memory import MemNet
from .ring import N_IDLE, Ring
from .route import Route, plan

__all__ = ["Breath", "BreathResult", "hearth"]


@dataclass(frozen=True)
class BreathResult:
    """One breath: what route it took, what it appended, what the world did."""

    route: Route
    heat: int
    offset: int
    appended: int
    collapse: int
    fingerprint: str


class Breath:
    """One world, advanced by feeding tears one at a time."""

    __slots__ = ("graph", "ledger", "memnet", "ring", "_cursor")

    def __init__(self, graph: SpacetimeGraph | None = None) -> None:
        self.graph = graph if graph is not None else SpacetimeGraph()
        self.memnet = MemNet()
        self.ring = Ring()
        self.ledger = FokenLedger()
        self._cursor = 0

    def anchor(self, tear: str) -> int:
        """Write ``tear`` as an immortal anchor at the next free ring slot."""
        for index in range(N_IDLE):
            if (self.ring.anchor_mask & (1 << index)) == 0:
                self.ring.set_anchor(index, 3 * ONE)
                return index
        raise ValueError("ring anchor table is full")

    def verdict(self) -> int:
        """Return the current ring verdict in {-1, 0, 1}."""
        return self.ring.verdict()

    def recall(self, cue: str) -> tuple[str, ...]:
        """Tears this breath has already eaten whose text contains ``cue``."""
        return self.memnet.recall(cue)

    def feed(self, tear: str) -> BreathResult:
        """Append a block for ``tear`` (unless empty), tick, and collapse."""
        n = self.graph.n_nodes
        route = plan(tear, n)

        if tear == "":
            # Empty tear: append nothing, leave the world exactly as it is.
            return BreathResult(
                route=route,
                heat=0,
                offset=n,
                appended=0,
                collapse=observer(self.graph),
                fingerprint=self.graph.fingerprint(),
            )

        k = BLOCK
        sig = signal(tear, k)
        first, appended = seed_block(self.graph, sig, n)
        self.memnet.remember(tear, first, appended, 1)
        self.ledger.record_compute(BLOCK, BLOCK)
        heat = caveman(sig)
        self.ring.tick()
        self._write_transient(heat)
        self.graph.tick(1)
        return BreathResult(
            route=route,
            heat=heat,
            offset=first,
            appended=appended,
            collapse=observer(self.graph),
            fingerprint=self.graph.fingerprint(),
        )

    def _write_transient(self, heat: int) -> None:
        """Roll one transient amplitude into the ring, skipping anchor slots."""
        for _ in range(N_IDLE):
            index = self._cursor
            self._cursor = (self._cursor + 1) % N_IDLE
            if (self.ring.anchor_mask & (1 << index)) == 0:
                self.ring.write(index, heat * ONE)
                return


def hearth(
    tears: Iterable[str], graph: SpacetimeGraph | None = None
) -> list[BreathResult]:
    """Feed ``tears`` through one ``Breath`` over ``graph``; return each result."""
    b = Breath(graph)
    return [b.feed(tear) for tear in tears]