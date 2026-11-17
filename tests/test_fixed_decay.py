from ultragraph.zerocpu.fixed import (
    ONE,
    decay_q16,
    decay_q16_trunc,
    fx_mul,
    pade_exp_neg_q16,
)


def test_decay_q16_matches_fx_mul_and_one_is_identity():
    assert decay_q16(ONE, ONE) == ONE
    assert decay_q16(12345, ONE) == 12345
    assert decay_q16(ONE, ONE // 2) == ONE // 2
    assert decay_q16(3 * ONE, ONE // 2) == fx_mul(3 * ONE, ONE // 2)


def test_pade_exp_neg_matches_reference_values():
    assert pade_exp_neg_q16(0) == ONE
    assert pade_exp_neg_q16(-(5 << 16)) == ONE
    assert pade_exp_neg_q16(40 << 16) == 0
    assert pade_exp_neg_q16((41 << 16) | 1) == 0
    # e^-1 = 0.3678794 * 65536 = 24109.5 -> 24109
    assert pade_exp_neg_q16(1 << 16) == 24109


def test_decay_q16_trunc_reaches_zero_where_rounding_pins():
    # Round-half-away-from-zero pins small amplitudes at +/-1 forever.
    assert decay_q16(1, ONE // 2) == 1
    assert decay_q16_trunc(1, ONE // 2) == 0
    assert decay_q16_trunc(-1, ONE // 2) == 0
    v = ONE
    for _ in range(17):
        v = decay_q16_trunc(v, ONE // 2)
    assert v == 0


def test_decay_q16_trunc_one_is_identity():
    assert decay_q16_trunc(12345, ONE) == 12345
    assert decay_q16_trunc(-12345, ONE) == -12345


def test_decay_q16_trunc_truncates_toward_zero():
    assert decay_q16_trunc(3, ONE // 2) == 1  # 1.5 -> 1, not 2
    assert decay_q16_trunc(-3, ONE // 2) == -1