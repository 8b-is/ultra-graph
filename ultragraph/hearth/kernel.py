"""Kernel: the packed-lane integer dot and the fixed block size.

``caveman`` packs a signal's ternary trits into a list of ints and runs the
existing ``fixed.fx_dot`` over it -- no new arithmetic, no floats.  ``BLOCK`` is
the fixed number of nodes appended per tear.  It is a constant, deliberately
*not* ``len(sig)``: tying the block to the signal would grow the world by a new
amount every tear.
"""

from __future__ import annotations

from ..zerocpu.fixed import fx_dot
from ..zerocpu.hope import Signal

__all__ = ["BLOCK", "caveman"]

#: Nodes appended per tear.  Fixed constant -- never ``len(sig)``.
BLOCK: int = 8


def caveman(sig: Signal) -> int:
    """Packed-lane dot of a signal's trits against themselves.  Integer only."""
    packed = [int(t) for t in sig.trits]
    return fx_dot(packed, packed)