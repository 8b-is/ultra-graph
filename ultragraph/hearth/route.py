"""Pure integer router: pick a lane from ``(tear, n, budget)`` and nothing else.

The decision is a pure function of the tear's own signal -- no I/O, no globals,
no live world, no keyword tables.  ``n`` is always passed in; the caller reads
``graph.n_nodes`` and hands it over.  Same ``(tear, n, budget)`` always yields
the same :class:`Route`.
"""

from __future__ import annotations

import enum

from ..zerocpu.hope import Signal, signal

__all__ = ["BUDGET", "Route", "plan"]

#: Default lane budget (one cache line of trits).  With append-only growth the
#: lane count rises monotonically, so ``Deep`` starts firing once the world
#: passes ``BUDGET`` nodes -- small world, think directly; big world, coarsen.
BUDGET: int = 64


class Route(enum.Enum):
    """Which lane a tear takes.  Members, not magic ints."""

    CAVEMAN = "caveman"
    DEEP = "deep"
    REFLECT = "reflect"


def plan(tear: str, n: int, budget: int = BUDGET) -> Route:
    """Route a tear from its signal shape.  Pure: no globals, no world, no I/O.

    ``sig = signal(tear, n)``; ``Deep`` if the lane count exceeds ``budget``
    (world outgrew the cache line), else ``Caveman`` when the trit balance is
    zero (perfectly centered, think directly), else ``Reflect``.
    """
    sig: Signal = signal(tear, n)
    if len(sig) > budget:
        return Route.DEEP
    if sig.balance() == 0:
        return Route.CAVEMAN
    return Route.REFLECT