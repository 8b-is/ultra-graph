"""Breath loop: fetch -> route -> append -> observe, one tear at a time.

``hearth`` is a thin driver over a :class:`Breath`, which owns one
``SpacetimeGraph``.  Each non-empty tear appends exactly ``BLOCK`` nodes, seeds
only that block, ticks the world once, and collapses an observer value.  The
world is never rewritten or evicted; fingerprints record the growing state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..zerocpu.hope import observer, signal
from ..zerocpu.spacetime import SpacetimeGraph
from .block import seed_block
from .kernel import BLOCK, caveman
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

    __slots__ = ("graph",)

    def __init__(self, graph: SpacetimeGraph | None = None) -> None:
        self.graph = graph if graph is not None else SpacetimeGraph()

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
        self.graph.tick(1)
        return BreathResult(
            route=route,
            heat=caveman(sig),
            offset=first,
            appended=appended,
            collapse=observer(self.graph),
            fingerprint=self.graph.fingerprint(),
        )


def hearth(
    tears: Iterable[str], graph: SpacetimeGraph | None = None
) -> list[BreathResult]:
    """Feed ``tears`` through one ``Breath`` over ``graph``; return each result."""
    b = Breath(graph)
    return [b.feed(tear) for tear in tears]