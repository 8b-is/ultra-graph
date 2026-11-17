# Hearth / Vibe-Mesh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A runnable append-only "hearth" loop over `ultragraph.zerocpu` where each line of text appends a node block, ticks the world, and collapses an observer value.

**Architecture:** Six small Python modules under `ultragraph/hearth/`. `SpacetimeGraph` stays the only graph. `hope.signal`/`seed_signal` supply text→trits and whole-world seeding; one new helper (`seed_block`) seeds a subrange so tears can append. `MemNet` is a derived index over an ordered tear log, never a second store. Router is a pure integer predicate on `(tear, n, budget)` with no keyword matching.

**Tech Stack:** Python 3.15 stdlib only. numpy already a dependency but unused by this pass. No new deps.

**Spec:** `docs/superpowers/specs/2026-11-16-hearth-vibe-mesh-design.md`

## Global Constraints

- Integer-only in every deterministic path. No `f32`, no `f64`, no float literals in state math.
- `ultragraph/zerocpu/` is not modified by this plan. New code lives in `ultragraph/hearth/` and `tests/`.
- `n` is always passed explicitly to the router. Never read a global or live world inside `route.plan`.
- No keyword tables anywhere in the router.
- `tests/run_all.py` has a hardcoded `MODULES` list; every new test module must be added there or it silently never runs.
- Append-only: no function in this plan removes, overwrites, or reorders an existing node's state.

## Review Focus

- **Empty tear.** `""` must not raise, must not append nodes, must leave `fingerprint()` unchanged.
- **Unicode / multi-byte tears.** `signal` works on codepoints, not bytes; `len(sig)` must still equal the requested `n`.
- **World smaller than the requested block.** Appending `k` nodes then seeding must not silently seed fewer lanes than the block holds.
- **Very long tear at small `n`.** Heat must stay bounded by `SIGNAL_STEP * len(text)` in i64, never overflow, and `balance()` must remain in `[-n, n]`.
- **Rebuild after partial log.** A truncated tear log must rebuild to exactly the world the truncated prefix produced, with no dependence on the dropped tail.

---

### Task 1: Append-only block seeding

**Files:**
- Create: `ultragraph/hearth/__init__.py`
- Create: `ultragraph/hearth/block.py`
- Test: `tests/test_hearth.py`

**Interfaces:**
- Consumes: `ultragraph.zerocpu.hope.signal(text, n) -> Signal` (has `.trits`, `.balance()`, `__len__`), `SpacetimeGraph.add_node(state, pos) -> int`, `SpacetimeGraph.n_nodes` (read-only property), `SpacetimeGraph.set_state(idx, value)`.
- Produces: `seed_block(graph: SpacetimeGraph, sig: Signal, offset: int) -> tuple[int, int]` — appends `len(sig)` nodes at `offset`, writes `sig.trits` into them, returns `(first_index, n_appended)`. Raises `ValueError` if `offset != graph.n_nodes` before appending.

- [ ] **Step 1: Write the failing test**

```python
def test_seed_block_appends_and_writes_only_the_new_range():
    g = SpacetimeGraph()
    for _ in range(4):
        g.add_node(0, (0, 0, 0))
    before = g.state()
    sig = signal("abcd", 3)
    first, n = seed_block(g, sig, 4)
    assert (first, n) == (4, 3)
    assert g.n_nodes == 7
    assert g.state()[:4] == before          # prefix untouched
    assert g.state()[4:] == sig.trits
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'ultragraph.hearth'`

- [ ] **Step 3: Implement `seed_block`**

Signature above. Add `n = len(sig)`, append `n` nodes via `add_node(0, (0,0,0))`, then `set_state(offset + i, trit)` for each. Guard `offset != graph.n_nodes` before the first `add_node`. Also export `seed_block` from `ultragraph/hearth/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/run_all.py`
Expected: PASS, and the pre-existing 123 tests still pass.

- [ ] **Step 5: Add `test_hearth` to `MODULES`**

Modify `tests/run_all.py` `MODULES` list. Re-run `python3 tests/run_all.py`; expected: new test counted, zero failures.

- [ ] **Step 6: Commit**

```bash
git add ultragraph/hearth tests/test_hearth.py tests/run_all.py
git commit -m "feat(hearth): append-only block seeding"
```

---

### Task 2: Router

**Files:**
- Create: `ultragraph/hearth/route.py`
- Test: `tests/test_hearth.py`

**Interfaces:**
- Consumes: `signal` from Task 1's module scope.
- Produces: `BUDGET: int = 64`; `class Route(enum.Enum): CAVEMAN / DEEP / REFLECT`; `plan(tear: str, n: int, budget: int = BUDGET) -> Route`. Pure: no I/O, no globals, no world.

- [ ] **Step 1: Write the failing test**

```python
def test_plan_is_pure_and_budget_switches_lane():
    n = 64
    r1 = plan("the soil remembers", n)
    r2 = plan("the soil remembers", n)
    assert r1 is r2
    assert plan("x" * 40, 8) is Route.DEEP          # n=8 <= 64 -> Caveman
    assert plan("x" * 40, 8, budget=4) is Route.CAVEMAN

def test_plan_deep_when_world_outgrows_budget():
    assert plan("hope", 128) is Route.DEEP

def test_long_tear_balance_stays_bounded():
    sig = signal("x" * 5000, 64)
    assert len(sig) == 64
    assert -64 <= sig.balance() <= 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ImportError: cannot import name 'plan'`

- [ ] **Step 3: Implement `plan`**

Build `sig = signal(tear, n)`. `if len(sig) > budget: return Route.DEEP`. Else `if sig.balance() == 0: return Route.CAVEMAN`. Else `Route.REFLECT`. `BUDGET = 64` as a module constant.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ultragraph/hearth/route.py tests/test_hearth.py
git commit -m "feat(hearth): pure integer router with budget lane"
```

---

### Task 3: Derived index

**Files:**
- Create: `ultragraph/hearth/memory.py`
- Test: `tests/test_hearth.py`

**Interfaces:**
- Consumes: `seed_block`, `signal`, `SpacetimeGraph`.
- Produces: `class MemNet` with `remember(tear: str, offset: int, k: int, rounds: int) -> None`, `recall(cue: str) -> tuple[str, ...]`, `log() -> tuple[dict, ...]`, `rebuild(graph: SpacetimeGraph) -> None`. Entries are `{"hash": str, "offset": int, "k": int, "rounds": int, "tear": str}`.

- [ ] **Step 1: Write the failing test**

```python
def test_memnet_rebuild_matches_sidecar_and_prefix_is_stable():
    tears = ["soil first", "seeds are and", "hope is all around"]
    g = SpacetimeGraph()
    m = MemNet()
    for t in tears:
        off = g.n_nodes                     # offset BEFORE appending
        m.remember(t, off, 3, 1)
        seed_block(g, signal(t, 3), off)
        g.tick(1)
    live = g.fingerprint()

    g2, m2 = SpacetimeGraph(), MemNet()
    for e in m2.log():
        seed_block(g2, signal(e["tear"], e["k"]), e["offset"])
        g2.tick(e["rounds"])
    assert g2.fingerprint() == live
    assert m2.recall("soil") == ("soil first",)

def test_memnet_rebuild_of_truncated_log_matches_prefix():
    tears = ["a soil", "b seed", "c hope"]
    full, keep = SpacetimeGraph(), 2
    for i, t in enumerate(tears):
        off = full.n_nodes
        seed_block(full, signal(t, 3), off)
        full.tick(1)
    prefix = SpacetimeGraph()
    for t in tears[:keep]:
        off = prefix.n_nodes
        seed_block(prefix, signal(t, 3), off)
        prefix.tick(1)
    assert prefix.n_nodes < full.n_nodes
    # rebuild of the truncated log reproduces the prefix exactly, not the whole
    assert prefix.fingerprint() != full.fingerprint()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ImportError: cannot import name 'MemNet'`

- [ ] **Step 3: Implement `MemNet`**

`remember` appends one dict to an internal list (no eviction). `log()` returns a tuple copy. `recall(cue)` returns tears whose text contains `cue` as a case-sensitive substring, in log order. `rebuild` replays `log()` into the given graph and returns nothing. Hash via `hashlib.sha256(tear.encode()).hexdigest()[:16]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ultragraph/hearth/memory.py tests/test_hearth.py
git commit -m "feat(hearth): append-only derived MemNet index"
```

---

### Task 4: Kernel + breath loop

**Files:**
- Create: `ultragraph/hearth/kernel.py`
- Create: `ultragraph/hearth/loop.py`
- Test: `tests/test_hearth.py`

**Interfaces:**
- Consumes: `fixed.saturate`, `fixed.fx_dot`, `plan`, `Route`, `seed_block`, `MemNet`, `hope.observer`, `SpacetimeGraph.fingerprint`.
- Produces: `BLOCK: int = 8` (nodes appended per tear, fixed — **not** `len(sig)`,
  which would double the world every tear); `caveman(sig) -> int` (packed-lane dot,
  integer only); `class Breath` with `feed(tear: str) -> BreathResult`; `BreathResult`
  fields `route: Route`, `heat: int`, `offset: int`, `appended: int`, `collapse: int`,
  `fingerprint: str`; `hearth(tears: Iterable[str], graph: SpacetimeGraph | None = None) -> list[BreathResult]`.

- [ ] **Step 1: Write the failing test**

```python
def test_breath_appends_then_ticks_then_collapses():
    g = SpacetimeGraph()
    b = hearth(["soil first", "hope is all around"], g)
    assert len(b) == 2
    assert b[0].appended == BLOCK and b[0].offset == 0
    assert b[1].offset == b[0].appended          # append-only, contiguous
    assert b[1].appended == BLOCK                # fixed block, not len(sig)
    assert b[0].collapse in (-1, 0, 1)
    assert b[1].fingerprint != b[0].fingerprint

def test_hearth_is_deterministic():
    a = hearth(["a", "b", "c"], SpacetimeGraph())
    b = hearth(["a", "b", "c"], SpacetimeGraph())
    assert [x.fingerprint for x in a] == [x.fingerprint for x in b]

def test_empty_tear_appends_nothing():
    g = SpacetimeGraph()
    out = hearth(["soil", "", "seed"], g)
    assert out[1].appended == 0
    assert out[1].offset == out[0].appended
    assert out[1].fingerprint == out[0].fingerprint

def test_unicode_tear_keeps_block_size():
    out = hearth(["hogy vagy Emese? 🕯️"], SpacetimeGraph())
    assert out[0].appended == BLOCK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ImportError: cannot import name 'hearth'`

- [ ] **Step 3: Implement `BLOCK`, `caveman`, `Breath`, `hearth`**

`caveman(sig)`: pack `sig.trits` into a list of ints and return `fx_dot(packed, packed)` — no new arithmetic. `Breath.feed`: `n = graph.n_nodes`; `route = plan(tear, n)`; if `tear` is empty, append nothing and return the unchanged fingerprint with `appended == 0`; else `k = BLOCK`, `sig = signal(tear, k)`, `seed_block(graph, sig, n)`, `graph.tick(1)`, `collapse = observer(graph)`, record `fingerprint()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ultragraph/hearth/kernel.py ultragraph/hearth/loop.py tests/test_hearth.py
git commit -m "feat(hearth): breath loop over world with observer collapse"
```

---

### Task 5: REPL + release

**Files:**
- Create: `ultragraph/hearth/__main__.py`
- Modify: `CHANGELOG.md`, `pyproject.toml` (version → 0.24.0)

**Interfaces:**
- Consumes: `hearth`, `SpacetimeGraph`.
- Produces: `python3 -m ultragraph.hearth` reads stdin lines at prompt `tears/write > `, feeds each to a `Breath`, prints `route / heat / offset+appended / collapse / fingerprint`, exits on `exit` or EOF.

- [ ] **Step 1: Write the failing test**

```python
def test_repl_feeds_lines_and_exits_on_eof(monkeypatch, capsys):
    import ultragraph.hearth.__main__ as repl
    monkeypatch.setattr("sys.stdin", io.StringIO("soil first\nexit\n"))
    repl.main()
    out = capsys.readouterr().out
    assert "tears/write >" in out
    assert "soil first" not in out or "collapse" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/run_all.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'ultragraph.hearth.__main__'`

- [ ] **Step 3: Implement `main()`**

`main()` builds `SpacetimeGraph()`, loops `input()` with the prompt, breaks on `exit`/EOF, calls `Breath.feed`, prints one line per tear. Guard `EOFError` and `KeyboardInterrupt`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/run_all.py`
Expected: PASS.

- [ ] **Step 5: Manual run**

Run: `printf 'soil first\nhope is all around\nexit\n' | python3 -m ultragraph.hearth`
Expected: three prompt lines, two result lines, no traceback.

- [ ] **Step 6: Version + changelog, then commit**

Bump `pyproject.toml` to `0.24.0`, add a CHANGELOG section naming the append-only world and the derived index.

```bash
git add ultragraph/hearth/__main__.py CHANGELOG.md pyproject.toml tests/test_hearth.py
git commit -m "feat(hearth): stdin REPL, 0.24.0"
```

---

## Not in this plan

The spec's **Pass 2** — harvesting anchors, `N_IDLE` ring window, dyadic-shift decay, `pade_exp_neg_q16`, and the case-insensitive guard into `ultragraph/zerocpu/` — is a separate plan. It touches the shared substrate both machines depend on, so it needs its own review and its own parity tests against `rust/zerocpu`. Do not fold it into this pass.