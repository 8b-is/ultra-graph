import io

from ultragraph.hearth.block import seed_block
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