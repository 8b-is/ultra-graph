"""Kernel: the packed-lane integer dot and the fixed block size.

``caveman`` packs a signal's ternary trits into a list of ints and runs the
existing ``fixed.fx_dot`` over it -- no new arithmetic, no floats.  ``BLOCK`` is
the fixed number of nodes appended per tear.  It is a constant, deliberately
*not* ``len(sig)``: tying the block to the signal would grow the world by a new
amount every tear.
"""

from __future__ import annotations

from ..zerocpu.fixed import FRAC_BITS, ONE, fx_dot
from ..zerocpu.hope import Signal

__all__ = ["BLOCK", "caveman"]

#: Nodes appended per tear.  Fixed constant -- never ``len(sig)``.
BLOCK: int = 8


def caveman(sig: Signal) -> int:
    """Count the signal's non-zero trits, using the Q16.16 dot.

    ``fx_dot`` is a fixed-point product: it returns ``round(total / 2**16)``.
    Feeding raw trits in ``{-1, 0, +1}`` therefore always rounds to ``0``.  Lanes
    are scaled to Q16.16 first, so the dot returns ``count * 2**16`` and the
    final shift yields the count itself -- integer only, no new arithmetic.
    """
    packed = [int(t) * ONE for t in sig.trits]
    return fx_dot(packed, packed) >> FRAC_BITS