//! Q16.16 fixed point, bit-compatible with `ultragraph/zerocpu/fixed.py`.
//!
//! A value is an `i64` holding `real * 2^16`.  Rounding is half-away-from-zero
//! and therefore symmetric, which is what makes two machines agree.
//!
//! Domain: `|value| < 2^46` so that a product fits in `i64`.  Dot products
//! accumulate in `i128`, so only the individual values have that bound.

pub const FRAC_BITS: u32 = 16;
pub const ONE: i64 = 1 << FRAC_BITS;
const HALF: i128 = (ONE >> 1) as i128;

/// Divide a raw Q32 product by `2^16`, rounding half away from zero.
pub fn round_shift(product: i64) -> i64 {
    round_shift128(product as i128) as i64
}

fn round_shift128(product: i128) -> i128 {
    if product >= 0 {
        (product + HALF) >> FRAC_BITS
    } else {
        -((-product + HALF) >> FRAC_BITS)
    }
}

/// Integer division rounded half away from zero. Panics when `den == 0`.
pub fn round_div(num: i64, den: i64) -> i64 {
    assert!(den != 0, "fixed-point division by zero");
    let (an, ad) = (num.abs(), den.abs());
    let mut q = an / ad;
    if (an % ad) * 2 >= ad {
        q += 1;
    }
    if (num < 0) == (den < 0) {
        q
    } else {
        -q
    }
}

/// Exact integer -> raw Q16.16.
pub fn from_int(value: i64) -> i64 {
    value << FRAC_BITS
}

/// Exact rational -> raw Q16.16 (same as Python `to_fx(Fraction(num, den))`).
pub fn from_ratio(num: i64, den: i64) -> i64 {
    round_div(num << FRAC_BITS, den)
}

pub fn fx_mul(a: i64, b: i64) -> i64 {
    round_shift(a * b)
}

pub fn fx_div(a: i64, b: i64) -> i64 {
    assert!(b != 0, "fixed-point division by zero");
    round_div(a << FRAC_BITS, b)
}

/// Dot product with a single rounding step at the end, accumulated in i128.
pub fn fx_dot(a: &[i64], b: &[i64]) -> i64 {
    assert_eq!(a.len(), b.len(), "length mismatch");
    let total: i128 = a
        .iter()
        .zip(b.iter())
        .map(|(x, y)| (*x as i128) * (*y as i128))
        .sum();
    round_shift128(total) as i64
}

/// Square root of a non-negative raw value, staying in Q16.16.
pub fn fx_sqrt(value: i64) -> i64 {
    assert!(value >= 0, "fx_sqrt of a negative value");
    (value << FRAC_BITS).isqrt()
}

/// Display/test conversion only -- never use in the deterministic path.
pub fn to_float(value: i64) -> f64 {
    value as f64 / ONE as f64
}

/// Nearest integer (round half away from zero).
pub fn to_int(value: i64) -> i64 {
    round_div(value, ONE)
}

/// Multiply a raw Q16.16 value by a Q16.16 decay factor, keeping Q16.16.
pub fn decay_q16(current: i64, factor: i64) -> i64 {
    round_shift(current * factor)
}

/// Like [`decay_q16`] but truncating toward zero, so repeated decay with
/// `factor < ONE` reaches exactly 0 instead of pinning at +/-1.
pub fn decay_q16_trunc(current: i64, factor: i64) -> i64 {
    let product = current * factor;
    if product >= 0 {
        product >> FRAC_BITS
    } else {
        -((-product) >> FRAC_BITS)
    }
}

/// Compute `e^(-x)` for `x` in Q16.16 using a [3/3] Padé approximant.
///
/// Returns `ONE` for `x <= 0` and `0` for `x >= 40 << FRAC_BITS`.
pub fn pade_exp_neg_q16(x: i64) -> i64 {
    if x <= 0 {
        return ONE;
    }
    if x >= 40 << FRAC_BITS {
        return 0;
    }
    const INV_LN2: i64 = 94548;
    const LN2_Q16: i64 = 45426;
    let k = (x * INV_LN2) >> 32;
    let r = x - k * LN2_Q16;
    let r2 = (r * r) >> FRAC_BITS;
    let r3 = (r * r2) >> FRAC_BITS;
    let num = (120 * ONE) - (60 * r) + (12 * r2) - r3;
    let den = (120 * ONE) + (60 * r) + (12 * r2) + r3;
    round_div(num << FRAC_BITS, den) >> k.min(32)
}

/// Clamp into the int8 node-byte range.
pub fn saturate_i8(value: i64) -> i8 {
    value.clamp(i8::MIN as i64, i8::MAX as i64) as i8
}
