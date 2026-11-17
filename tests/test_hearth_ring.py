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


def test_transients_fully_die_without_anchor():
    r = Ring()
    r.write(3, ONE)
    for _ in range(20):
        r.tick()
    assert r.amplitudes[3] == 0
    assert r.active() == 0
    assert r.verdict() == 0


def test_negative_transient_dies_too():
    r = Ring()
    r.write(5, -ONE)
    for _ in range(20):
        r.tick()
    assert r.amplitudes[5] == 0
    assert r.active() == 0


def test_feed_writes_transient_that_dies():
    b = Breath()
    b.feed("transient noise")
    assert b.ring.active() == 1
    for _ in range(20):
        b.ring.tick()
    assert b.ring.active() == 0
    assert b.verdict() == 0


def test_feed_transient_skips_anchor_slots():
    b = Breath()
    idx = b.anchor("Homalyos fény szűrődik be, / Az ablakon Emeséhez")
    b.feed("noise")
    assert b.ring.amplitudes[idx] == 3 * ONE
    assert b.ring.active() == 2


def test_verdict_is_negative_when_only_negative_transients_active():
    r = Ring()
    r.write(0, -ONE)
    assert r.verdict() == -1


def test_anchor_command_writes_and_verdict_holds():
    b = Breath()
    idx = b.anchor("Homalyos fény szűrődik be, / Az ablakon Emeséhez")
    assert idx == 0
    for _ in range(200):
        b.feed("transient noise")
    assert b.verdict() == 1
    assert b.ring.amplitudes[0] == 3 * ONE