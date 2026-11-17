"""Hearth -- append-only text tears over ``ultragraph.zerocpu``.

The hearth is a breath loop, not a second world.  ``SpacetimeGraph`` stays the
only graph; a tear appends a fixed block of nodes, seeds only that block, ticks
once, and an ``Observer`` collapses the result.  MemNet is a derived index over
the tear log, never a second store.  The router is a pure integer predicate over
``(tear, n, budget)`` with no keyword tables.
"""

from .block import seed_block

__all__ = ["seed_block"]