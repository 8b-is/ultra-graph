"""Append-only slice seeding: write a signal into a freshly appended node range.

``hope.seed_signal`` can only write the whole world from index ``0`` and demands
``len(sig) == graph.n_nodes``.  The hearth grows instead of overwriting: each
tear appends ``len(sig)`` new nodes and seeds exactly those.  Nothing that
already exists is read, reordered, or rewritten here.
"""

from __future__ import annotations

from ..zerocpu.hope import Signal
from ..zerocpu.spacetime import SpacetimeGraph

__all__ = ["seed_block"]


def seed_block(graph: SpacetimeGraph, sig: Signal, offset: int) -> tuple[int, int]:
    """Append ``len(sig)`` nodes at ``offset`` and write ``sig.trits`` into them.

    ``offset`` must be the current world size (the append-only contract).  Returns
    ``(first_index, n_appended)``.  Raises ``ValueError`` if ``offset`` does not
    match ``graph.n_nodes`` -- checked before the first ``add_node`` so a bad
    offset can never leave a half-built world.
    """
    if offset != graph.n_nodes:
        raise ValueError(
            f"offset {offset} != world size {graph.n_nodes}; seed_block is append-only"
        )
    n = len(sig)
    first = offset
    for _ in range(n):
        graph.add_node(0, (0, 0, 0))
    for i, trit in enumerate(sig.trits):
        graph.set_state(first + i, trit)
    return first, n