"""Exact rational accounting for compute savings and kept ratios."""

from __future__ import annotations

import math

__all__ = ["FokenLedger", "Fraction"]


class Fraction:
    """Reduced rational number ``num / den`` with exact value equality."""

    __slots__ = ("num", "den")

    def __init__(self, num: int, den: int = 1) -> None:
        n, d = int(num), int(den)
        if d == 0:
            self.num = 0
            self.den = 1
            return
        if d < 0:
            n = -n
            d = -d
        g = math.gcd(n, d)
        if g > 1:
            n //= g
            d //= g
        self.num = n
        self.den = d

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Fraction):
            return NotImplemented
        return self.num == other.num and self.den == other.den

    def __hash__(self) -> int:
        return hash((self.num, self.den))

    def __repr__(self) -> str:
        return f"Fraction({self.num}, {self.den})"

    def __str__(self) -> str:
        return f"{self.num}/{self.den}"


class FokenLedger:
    """Accumulates integer ``(original, kept)`` counts with exact rational totals."""

    __slots__ = ("_original", "_kept")

    def __init__(self) -> None:
        self._original = 0
        self._kept = 0

    def is_empty(self) -> bool:
        return self._original == 0

    def record_compute(self, original: int, kept: int) -> None:
        self._original += int(original)
        self._kept += int(kept)

    def get_savings(self) -> Fraction:
        saved = self._original - self._kept
        if self._original == 0:
            return Fraction(0, 1)
        return Fraction(saved, self._original)

    def get_kept_ratio(self) -> Fraction:
        if self._original == 0:
            return Fraction(0, 1)
        return Fraction(self._kept, self._original)