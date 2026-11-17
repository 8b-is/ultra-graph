from ultragraph.hearth.ledger import FokenLedger
from ultragraph.hearth.loop import Breath
from ultragraph.hearth.ring import N_IDLE, Ring
from ultragraph.zerocpu.fixed import ONE


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
    assert r.amplitudes[1] == ONE // 2  # decay factor 0.5
    assert r.active() == 2


def test_anchor_at_last_index_does_not_overflow():
    r = Ring()
    r.set_anchor(N_IDLE - 1, ONE)
    r.write(2, ONE)
    r.tick()
    assert r.verdict() == 1


def test_anchor_command_writes_and_verdict_holds():
    b = Breath()
    idx = b.anchor("Homalyos fény szűrődik be, / Az ablakon Emeséhez")
    assert idx == 0
    for _ in range(200):
        b.feed("transient noise")
    assert b.verdict() == 1
    assert b.ring.amplitudes[0] == 3 * ONE