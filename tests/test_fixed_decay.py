from ultragraph.zerocpu.fixed import ONE, decay_q16, fx_mul, pade_exp_neg_q16


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