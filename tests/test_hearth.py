import io

from ultragraph.hearth.block import seed_block
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
