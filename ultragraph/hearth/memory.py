"""MemNet -- a derived index over the ordered tear log, never a second store.

The source of truth is the sequence of ``(tear, offset, k, rounds)`` entries.
``MemNet`` holds that log in memory (append-only, no eviction) and can replay it
into a fresh ``SpacetimeGraph``.  Because the index is *derived* by replay, it
cannot drift from the world: rebuild the graph from the log and the fingerprint
matches, by construction.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..zerocpu.spacetime import SpacetimeGraph
from .block import seed_block
from ..zerocpu.hope import signal

__all__ = ["MemNet"]


def _tear_hash(tear: str) -> str:
    """First 16 hex chars of SHA-256 over the tear's UTF-8 bytes."""
    return hashlib.sha256(tear.encode()).hexdigest()[:16]


class MemNet:
    """Append-only in-memory tear log with substring recall and replay."""

    __slots__ = ("_log",)

    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []

    def remember(self, tear: str, offset: int, k: int, rounds: int) -> None:
        """Append one entry.  Never evicts, never reorders, never rewrites."""
        self._log.append(
            {
                "hash": _tear_hash(tear),
                "offset": int(offset),
                "k": int(k),
                "rounds": int(rounds),
                "tear": tear,
            }
        )

    def recall(self, cue: str) -> tuple[str, ...]:
        """Tears whose text contains ``cue`` as a case-sensitive substring, in log order."""
        return tuple(e["tear"] for e in self._log if cue in e["tear"])

    def log(self) -> tuple[dict[str, Any], ...]:
        """A tuple copy of the ordered log."""
        return tuple(self._log)

    def rebuild(self, graph: SpacetimeGraph) -> None:
        """Replay the log into ``graph``: ``seed_block`` then ``tick(rounds)`` per entry."""
        for e in self._log:
            seed_block(graph, signal(e["tear"], e["k"]), e["offset"])
            graph.tick(e["rounds"])