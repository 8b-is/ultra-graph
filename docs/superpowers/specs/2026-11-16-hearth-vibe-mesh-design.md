# Hearth / Vibe-Mesh — design

Date: 2026-11-16 · Status: approved, pending plan · Substrate: `ultragraph.zerocpu` @ 0.23.0 (`0f5adb5`)

## Decisions (settled with the user)

1. **Substrate = `ultragraph.zerocpu`.** Canonical. The 16 GB box works the same
   repo; a second implementation here would fork it.
2. **The world grows per tear. Append-only.** Each tear appends a block of `k`
   nodes, seeds only that block, then `tick(1)`. Nothing is ever overwritten or
   evicted. MemNet's "node range it seeded" is therefore real.
3. **`mem8-memnet` is not built as a crate.** It re-declares `Trit`, `MemNet`,
   `observer_variance` which `zerocpu` already has. Its three genuinely missing
   ideas get harvested into `zerocpu` instead (see Harvest).

## Intent

One command that runs tonight: raw text ("tears") goes in, the graph grows
deterministically, an observer reads a value out. Routing + memory + kernel over
existing `zerocpu` primitives. One process, no new dependencies, no server.

## Why this shape

`zerocpu` already contains every primitive the sketches assume:

| Sketch wants | Real thing |
| --- | --- |
| `UltraGraph` with `tick()`, `nodes.get_mut()`, `node.variance` | `zerocpu.spacetime.SpacetimeGraph` — `add_node/add_edge/tick(n)/state()/fingerprint()` |
| "Shawshank hack the root node, variance → 99.9" | `zerocpu.hope.seed_signal(graph, signal)` — writes state from text |
| Hope cascade / butterfly | `zerocpu.hope.resonate(...)` + `hope.observer(graph)` |
| Ternary quantizer `Q_Δ(z)` | `zerocpu.fixed.saturate` / `to_fx` (Q16.16) |
| Caveman Ultra bitwise kernel | `zerocpu.fixed.fx_dot / fx_matvec` (NEON twin in `rust/zerocpu/src/neon.rs`) |
| LOD compressor | `zerocpu.lod.coarsen / partition / density_stats` |
| p/q compiler | `zerocpu.pqq.resolve / run_pqq / write_bundle` |
| HERMES / OPENCLAW indices | *nothing* — this is the actual gap |

Verified, not assumed:

- `ultragraph/zerocpu/` contains **no** `f32`/`f64` anywhere. No-float is done.
- `resonate()` (`hope.py:129`) is already the breath loop:
  `signal` → `seed_signal` → `tick(rounds)` → `trace` → `observer.of_world()`.
  Hearth calls it; it does not reimplement it.
- `seed_signal` (`hope.py:101`) requires `len(sig) == graph.n_nodes` exactly and
  writes **every** node via `set_state`. It cannot target a subrange. Append-only
  therefore needs one new helper (below).
- `Signal.balance()` = `sum(trits)`, `len(sig)` = lane count, `total_heat()` is
  Q16.16 heat.

## Harvest into `zerocpu` (from the rejected `mem8-memnet` drop)

These four do not exist in `zerocpu` (`grep anchor|N_IDLE|half_life|decay` → empty):

1. **Anchor nodes** — non-decaying nodes that ring eviction cannot remove.
2. **`N_IDLE` ring window** — bounded memory, fixed size, no heap growth.
3. **Dyadic-shift decay** — `amp >> (elapsed >> half_life_shift)`, exact, no
   transcendentals. Sits beside `fx_sqrt` in `fixed.py`.
4. **Case-insensitive guard** — `eq_ignore_ascii_case` over a byte window.

The dyadic Padé `e^-x` from the same drop was checked by hand (x=1.0 → `k=1`,
`r=20110`, num/den → 48215, `>>1` = 24107 vs true 24109, 2 ulp) and is correct.
It goes in `fixed.py` as `pade_exp_neg_q16`, not into a new crate.

## Goals

1. One command that runs tonight: tears in → deterministic graph growth + observer out.
2. A router whose decision is a pure function of `(tear, n)`. No keyword tables.
3. An append-only MemNet index that cannot drift, because it is *derived* by
   replaying the tear log.
4. Integer-only in every deterministic path. No `f32`/`f64`.

## Non-goals

- 1-bit Riva inference (external process; hearth never fakes a forward pass).
- HTTP / Axum bridge, browser extension. Next pass; loopback only (8083, never
  8080 — foken-web owns 8080 on this box).
- MCP/ACP plugin surface, 8B model integration.
- Hungarian / Waiyan / @w3ighT-p(roz) linguistic LOD.
- LAN work migration. Discovery only.
- A second `UltraGraph` type, a second `Trit`, a second `MemNet`.

## Anti-goals

- Forking the substrate. One implementation, two languages, pinned parity.
- Float drift in the deterministic path.
- Mutation behind the graph's back: any function that seeds without saying so.
- Keyword tables in the router — unfalsifiable, and already removed from `hope.py`
  once for this reason.

## Design

### Modules (new, under `ultragraph/hearth/`)

```
route.py     plan(tear, n, budget) -> Route      # Smart-Tree / FANOUT, pure
memory.py    MemNet: remember / recall / rebuild  # HERMES + OPENCLAW, derived
kernel.py    caveman(tear, world) -> Report        # thin wrapper over fixed.*
loop.py      hearth(world, tears) -> Session       # breath: fetch→route→append→observe
block.py     seed_block(graph, sig, offset)       # append-only slice seeding
__main__.py  REPL: "tears/write >" on stdin
```

`block.seed_block` is the one new primitive. `seed_signal` can only write the
whole world from index 0; append-only needs to seed `[offset, offset+len)`. It
lives in `hearth/`, not `zerocpu/` — the shared substrate stays untouched by this
pass except for the four harvest items, which land as their own commit.

### Routing

`route.plan` is a pure integer predicate over the tear's *signal*:

```
sig  = hope.signal(tear, n)          # n = world size BEFORE this tear
heat = sig.balance()                 # trit imbalance, [-n, n]
lane = len(sig)                      # == n
Route::Caveman   if heat == 0        and lane <= BUDGET
Route::Deep      if lane  >  BUDGET
Route::Reflect   otherwise
```

`n` is a parameter, never read from a global or the live world. Same `(tear, n,
budget)` ⇒ same route, always. That is the whole determinism claim for routing.

`BUDGET` default = 64 lanes (one cache line of trits). With append-only growth
`lane` rises monotonically, so `Deep` starts firing once the world passes 64
nodes and never stops — which is the intended reading of the notebook: small
world, think directly; big world, coarsen first.

### Memory

`MemNet` is an **index, not a store**. Source of truth is the ordered tear log.

```python
class MemNet:
    def remember(self, tear: str, offset: int, k: int) -> None
    def recall(self, cue: str) -> tuple[str, ...]     # tears whose blocks overlap
```

On-disk form: `world.ugmz` (the graph) + a JSON sidecar of
`(tear_hash, offset, k, rounds)`. Rebuild = replay the log in order, calling
`seed_block` then `tick(rounds)` for each entry. If the sidecar and the replay
ever disagree, the replay wins — asserted by one test.

### Kernel

`kernel.caveman` packs `sig.trits` into i8 lanes and calls the existing
`fx_dot` / `saturate`. It adds no arithmetic. `dot_i8` (the inner loop of every
tick) still has no g8t capsule — standing follow-up.

### Deep route

`lod.partition(n, edges, k)` is a free function returning a `Partition`; it does
not mutate a graph. Deep therefore means: coarsen the **node index**, then seed
only the nodes in block 0 of the resulting partition. Index-level, explicit,
no hidden graph mutation.

### LAN discovery

`--discover` broadcasts one UDP datagram to `255.255.255.255:8765`, stdlib
socket only, payload `{role, cores, mem_gb, ug, fingerprint}`. Receivers print.
No work migrates, no state crosses the wire. Presence only, so the 64 GB "Ocean"
and the 16 GB "Hearth" are visible before anything depends on it.

## Tonight's demo

```
python3 -m ultragraph.hearth
tears/write > <the master script>
```

Per tear prints: route, signal heat, node range appended, `observer()` value,
world `fingerprint()`. Same tears in the same order ⇒ same fingerprint, always.

## Verification

- `python3 tests/run_all.py` — existing 123 tests stay green. **`test_hearth`
  must be added to the hardcoded `MODULES` list or it silently never runs.**
- new `tests/test_hearth.py`:
  - determinism: same tear list ⇒ identical `fingerprint()` and observer trace;
  - append-only: node count after N tears == sum of block sizes, and no state
    written by tear `i` is changed by tear `i+1`;
  - router purity: `plan()` same output for same `(tear, n, budget)` across runs;
  - index honesty: `MemNet` rebuilt from the log equals the sidecar it wrote;
  - integer-only: every value in `state()` is `isinstance(int)`, and no float
    token appears in `hearth/` source.
- `cargo test` in `rust/zerocpu` stays green (untouched this pass).

## Sizes / sequencing

Pass 1 (tonight): `route.py`, `memory.py`, `kernel.py`, `block.py`, `loop.py`,
`__main__.py`, one test file, `MODULES` entry, CHANGELOG + bump to 0.24.0.
Python only.

Pass 2: harvest commit into `zerocpu` (anchors, `N_IDLE`, dyadic shift,
`pade_exp_neg_q16`, case-insensitive guard) + tests.

Pass 3: Rust twin `rust/zerocpu/src/bin/hearth.rs` + parity test.
Pass 4: loopback HTTP bridge (8083) + browser-extension POST.
Pass 5: `dot_i8` g8t capsule.

## Open

Nothing blocking. `BUDGET=64` is my call and is one line to change.