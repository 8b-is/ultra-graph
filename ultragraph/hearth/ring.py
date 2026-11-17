"""Bounded ring window with immortal anchors and dyadic Q16.16 decay."""

from __future__ import annotations

from ..zerocpu.fixed import ONE, decay_q16_trunc

__all__ = ["N_IDLE", "Ring"]

#: Number of slots in the idle ring window.
N_IDLE: int = 64


class Ring:
    """Fixed-size Q16.16 amplitude ring with anchor bitmask and active mask."""

    __slots__ = ("amplitudes", "anchor_mask", "active_mask", "decay_factor")

    def __init__(self, decay_factor: int = ONE // 2) -> None:
        self.amplitudes: list[int] = [0] * N_IDLE
        self.anchor_mask: int = 0
        self.active_mask: int = 0
        self.decay_factor: int = int(decay_factor)

    def set_anchor(self, index: int, amplitude_q16: int) -> None:
        """Pin ``index`` as an immortal anchor with ``amplitude_q16``."""
        if not 0 <= index < N_IDLE:
            raise IndexError(f"ring index {index} out of range [0, {N_IDLE})")
        amp = int(amplitude_q16)
        self.amplitudes[index] = amp
        bit = 1 << index
        self.anchor_mask |= bit
        if amp != 0:
            self.active_mask |= bit
        else:
            self.active_mask &= ~bit

    def write(self, index: int, amplitude_q16: int) -> None:
        """Write a transient value at ``index`` unless it is an anchor."""
        if not 0 <= index < N_IDLE:
            raise IndexError(f"ring index {index} out of range [0, {N_IDLE})")
        if (self.anchor_mask & (1 << index)) != 0:
            return
        amp = int(amplitude_q16)
        self.amplitudes[index] = amp
        bit = 1 << index
        if amp != 0:
            self.active_mask |= bit
        else:
            self.active_mask &= ~bit

    def tick(self) -> None:
        """Advance one step: decay all active non-anchor amplitudes in place."""
        to_decay = self.active_mask & ~self.anchor_mask
        while to_decay:
            bit = to_decay & -to_decay
            to_decay ^= bit
            index = bit.bit_length() - 1
            amp = decay_q16_trunc(self.amplitudes[index], self.decay_factor)
            self.amplitudes[index] = amp
            if amp == 0:
                self.active_mask &= ~bit

    def verdict(self) -> int:
        """Return +1 if any anchor is active, else the sign of active amplitudes."""
        if (self.active_mask & self.anchor_mask) != 0:
            return 1
        total = 0
        bits = self.active_mask
        while bits:
            bit = bits & -bits
            bits ^= bit
            total += self.amplitudes[bit.bit_length() - 1]
        return 0 if total == 0 else (1 if total > 0 else -1)

    def active(self) -> int:
        """Number of currently active slots in the ring."""
        return self.active_mask.bit_count()