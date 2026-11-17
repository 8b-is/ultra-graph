# Hearth Pass 2 — Anchors, Windowed Decay, Exact Ledger

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Emese anchor immortal, bound memory with an `N_IDLE` window, decay amplitudes with exact integer math, and account every compression with a reduced rational.

**Architecture:** Pure decay functions join `zerocpu/fixed.py` (mirrored to Rust, parity-tested). The ring, anchor masks, and ledger are new modules under `ultragraph/hearth/` — deliberately **not** in `zerocpu`, so `SpacetimeGraph` semantics and the existing 123 tests cannot move.

**Tech Stack:** Python 3.15 stdlib, integer only. Rust twin in `rust/zerocpu` for the two new `fixed` functions.

**Spec:** `docs/superpowers/specs/2026-11-16-hearth-vibe-mesh-design.md` (Pass 2 section)

## Global Constraints

- Integer-only. No `f32`/`f64`, no float literals in any computed value.
- Do **not** add inline `asm!`. This machine is `arm64`; the submitted `decay_q16`
  asm block is x86-64 (`mov eax`/`imul ecx`/`shrd`) and will not compile. LLVM
  already lowers the portable `(a * b) >> 16` to `mul` + `sshr` on aarch64.
- Do not modify `SpacetimeGraph` behaviour or `hope.py`. Existing tests must stay green.
- Any new `zerocpu` function needs a Rust twin in `rust/zerocpu/src/fixed.rs` and a
  parity case in `rust/zerocpu/tests/`.
- `tests/run_all.py` has a hardcoded `MODULES`; new test modules must be added.

## Review Focus

- **Empty ledger.** `get_kept_ratio()` on zero compute must not panic. Define it.
- **Anchor at index 63.** Mask shifts must not overflow `u64` / Python ints.
- **Decay factor of exactly `ONE`.** Must be a no-op, not a rounding drift.
- **`pade_exp_neg_q16` at the tail.** `x` past the `40 << 16` cutoff returns 0 without dividing by zero.
- **Fraction without reduction.** `2/4` and `1/2` must compare equal, or equality is a lie.

---

### Task 1: Exact decay primitives in `fixed`

**Files:**
- Modify: `ultragraph/zerocpu/fixed.py` (add two functions, extend `__all__`)
- Modify: `rust/zerocpu/src/fixed.rs`
- Modify: `rust/zerocpu/tests/` (parity case)
- Test: `tests/test_fixed_decay.py`

**Interfaces:**
- Consumes: existing `FRAC_BITS = 16`, `ONE = 1 << 16`, `_round_shift`.
- Produces:
  - `decay_q16(current: int, factor: int) -> int` — `(current * factor) >> 16` with round-half-away-from-zero, matching `fx_mul`.
  - `pade_exp_neg_q16(x: int) -> int` — `e^-x` for `x` in Q16.16, `[3/3]` Padé with `x = k·ln2 + r`, returns Q16.16. Returns `ONE` for `x <= 0`, `0` for `x > 40 << 16`.

- [ ] **Step 1: Write the failing tests**

```python
def test_decay_q16_matches_fx_mul_and_one_is_identity():
    assert decay_q16(ONE, ONE) == ONE
    assert decay_q16(12345, ONE) == 12345
    assert decay_q16(ONE, ONE // 2) == ONE // 2

def test_pade_exp_neg_matches_reference_values():
    assert pade_exp_neg_q16(0) == ONE
    assert pade_exp_neg_q16(-(5 << 16)) == ONE
    assert pade_exp_neg_q16(40 << 16) == 0
    assert pade_exp_neg_q16((41 << 16) | 1) == 0
    # e^-1 = 0.3678794 * 65536 = 24109.5 -> 24109
    assert pade_exp_neg_q16(1 << 16) == 24109
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ImportError: cannot import name 'decay_q16'`

- [ ] **Step 3: Implement both in `ultragraph/zerocpu/fixed.py`**

`decay_q16` delegates to `fx_mul`. `pade_exp_neg_q16`: `inv_ln2 = 94548`, `ln2_q16 = 45426`, `k = (x * inv_ln2) >> 32`, `r = x - k * ln2_q16`, Padé `(120 - 60r + 12r² - r³) / (120 + 60r + 12r² + r³)` evaluated in Q16.16, then `>> k` clamped to 32. Add both to `__all__`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Mirror to Rust and prove parity**

Add `decay_q16` and `pade_exp_neg_q16` to `rust/zerocpu/src/fixed.rs` with the same
integer ops, add a parity test beside the existing ones, run `cargo test`.

- [ ] **Step 6: Commit**

```bash
git add ultragraph/zerocpu/fixed.py rust/zerocpu tests/test_fixed_decay.py tests/run_all.py
git commit -m "feat(fixed): exact integer decay and Pade exp_neg"
```

---

### Task 2: Ring with anchors

**Files:**
- Create: `ultragraph/hearth/ring.py`
- Test: `tests/test_hearth_ring.py`

**Interfaces:**
- Consumes: `decay_q16` from Task 1.
- Produces: `N_IDLE: int = 64`; `class Ring` with `set_anchor(index: int, amplitude_q16: int) -> None`, `write(index: int, amplitude_q16: int) -> None`, `tick() -> None`, `verdict() -> int`, `active() -> int`.

- [ ] **Step 1: Write the failing tests**

```python
def test_anchor_never_decays_and_holds_verdict():
    r = Ring()
    r.set_anchor(0, 3 * ONE)
    for _ in range(5000):
        r.tick()
    assert r.amplitudes[0] == 3 * ONE
    assert r.verdict() == 1

def test_transients_decay_and_leave_the_active_mask():
    r = Ring()
    r.set_anchor(0, ONE)
    r.write(1, ONE)
    r.tick()
    assert r.amplitudes[1] == ONE // 2      # decay factor 0.5
    assert r.active() == 2

def test_anchor_at_last_index_does_not_overflow():
    r = Ring()
    r.set_anchor(N_IDLE - 1, ONE)
    r.write(2, ONE)
    r.tick()
    assert r.verdict() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'ultragraph.hearth.ring'`

- [ ] **Step 3: Implement `Ring`**

`amplitudes: list[int]` length `N_IDLE`; `anchor_mask: int`; `active_mask: int`;
`decay_factor: int = ONE // 2`. `tick` iterates `to_decay = active_mask & ~anchor_mask`
with `bit = to_decay & -to_decay` and `index = bit.bit_length() - 1`; applies
`decay_q16`; clears the bit from `active_mask` when the amplitude reaches 0.
`verdict()` returns `1` when `active_mask & anchor_mask` is non-zero, else the
sign of the summed active amplitudes (`-1`, `0`, or `1`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ultragraph/hearth/ring.py tests/test_hearth_ring.py tests/run_all.py
git commit -m "feat(hearth): anchored ring with bitmask decay"
```

---

### Task 3: Exact rational ledger

**Files:**
- Create: `ultragraph/hearth/ledger.py`
- Test: `tests/test_hearth_ledger.py`

**Interfaces:**
- Produces: `class Fraction` with `num: int`, `den: int`, `__eq__` by reduced value, `__str__` as `"n/d"`; `class FokenLedger` with `record_compute(original: int, kept: int) -> None`, `get_savings() -> Fraction`, `get_kept_ratio() -> Fraction`, `is_empty() -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
def test_fraction_is_reduced_and_equality_is_by_value():
    assert Fraction(2, 4) == Fraction(1, 2)
    assert str(Fraction(3, 10)) == "3/10"

def test_ledger_is_exact_for_thirds():
    led = FokenLedger()
    for _ in range(3):
        led.record_compute(1, 0)
    assert led.get_savings() == Fraction(3, 3)

def test_ledger_on_empty_does_not_divide_by_zero():
    led = FokenLedger()
    assert led.is_empty()
    assert led.get_savings() == Fraction(0, 1)
    assert led.get_kept_ratio() == Fraction(0, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'ultragraph.hearth.ledger'`

- [ ] **Step 3: Implement**

`Fraction` normalises sign into the numerator and divides both parts by
`math.gcd`, returning `Fraction(0, 1)` for a zero denominator rather than raising —
the submitted `assert!(den != 0)` panics on an empty ledger, which is the common
first call. `FokenLedger` accumulates `original`/`kept` and returns
`Fraction(saved, original)`, or `Fraction(0, 1)` when `original == 0`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ultragraph/hearth/ledger.py tests/test_hearth_ledger.py tests/run_all.py
git commit -m "feat(hearth): exact rational ledger"
```

---

### Task 4: Anchor command + version

**Files:**
- Modify: `ultragraph/hearth/__main__.py`
- Modify: `ultragraph/hearth/loop.py`
- Modify: `CHANGELOG.md`, `pyproject.toml` (→ 0.25.0)
- Test: `tests/test_hearth_ring.py`

**Interfaces:**
- Consumes: `Ring`, `FokenLedger`.
- Produces: `Breath.anchor(tear: str) -> int` (writes the tear as an anchor at the
  next free index, returns its index); REPL commands `anchor <text>` and `verdict`.

- [ ] **Step 1: Write the failing test**

```python
def test_anchor_command_writes_and_verdict_holds():
    b = Breath()
    idx = b.anchor("Homalyos fény szűrődik be, / Az ablakon Emeséhez")
    assert idx == 0
    for _ in range(200):
        b.feed("transient noise")
    assert b.verdict() == 1
    assert b.ring.amplitudes[0] == 3 * ONE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/run_all.py`
Expected: FAIL, `AttributeError: 'Breath' object has no attribute 'anchor'`

- [ ] **Step 3: Implement**

`Breath` owns a `Ring` and a `FokenLedger`. `feed` records compute
`(BLOCK, BLOCK)` on every non-empty tear. `anchor` writes at the lowest index not
already an anchor, amplitude `3 * ONE`. REPL prints `anchor=N` on write and the
`verdict()` on demand.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Manual run**

Run:
```
printf 'anchor Homalyos fenyeszedik be, Az ablakon Emeséhez\nnoise\nnoise\nverdict\nexit\n' | python3 -m ultragraph.hearth
```
Expected: anchor accepted, two noise lines, verdict `1`.

- [ ] **Step 6: Version + changelog + commit**

```bash
git add ultragraph/hearth CHANGELOG.md pyproject.toml tests/test_hearth_ring.py
git commit -m "feat(hearth): Emese anchor, verdict, 0.25.0"
```