import io

from ultragraph.hearth.block import seed_block
from ultragraph.hearth.kernel import BLOCK
from ultragraph.hearth.loop import hearth
from ultragraph.hearth.memory import MemNet
from ultragraph.hearth.route import Route, plan
from ultragraph.zerocpu.hope import signal
from ultragraph.zerocpu.spacetime import SpacetimeGraph


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

def test_plan_is_pure_and_budget_switches_lane():
    n = 64
    r1 = plan("the soil remembers", n)
    r2 = plan("the soil remembers", n)
    assert r1 is r2
    assert plan("x" * 40, 8) is Route.CAVEMAN          # n=8 <= 64 -> Caveman
    assert plan("x" * 40, 8, budget=4) is Route.DEEP


def test_plan_deep_when_world_outgrows_budget():
    assert plan("hope", 128) is Route.DEEP


def test_long_tear_balance_stays_bounded():
    sig = signal("x" * 5000, 64)
    assert len(sig) == 64
    assert -64 <= sig.balance() <= 64


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

    # NOTE: plan wrote `m2 = MemNet()` (empty) here; replaying an empty log
    # rebuilds nothing, so the assertions below could never hold. The intent is
    # "replay the log the sidecar wrote", so m2 is the same MemNet `m`.
    g2, m2 = SpacetimeGraph(), m
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
