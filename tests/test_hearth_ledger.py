from ultragraph.hearth.ledger import FokenLedger, Fraction


def test_fraction_is_reduced_and_equality_is_by_value():
    assert Fraction(2, 4) == Fraction(1, 2)
    assert str(Fraction(3, 10)) == "3/10"


def test_ledger_is_exact_for_thirds():
    led = FokenLedger()
    for _ in range(3):
        led.record_compute(1, 0)
    assert led.get_savings() == Fraction(3, 3)


def test_record_compute_rejects_kept_over_original():
    led = FokenLedger()
    try:
        led.record_compute(1, 5)
    except ValueError:
        pass
    else:
        raise AssertionError("ledger accepted kept > original")


def test_record_compute_rejects_negative_counts():
    led = FokenLedger()
    for original, kept in ((-1, 0), (1, -1)):
        try:
            led.record_compute(original, kept)
        except ValueError:
            pass
        else:
            raise AssertionError(f"ledger accepted ({original}, {kept})")


def test_ledger_on_empty_does_not_divide_by_zero():
    led = FokenLedger()
    assert led.is_empty()
    assert led.get_savings() == Fraction(0, 1)
    assert led.get_kept_ratio() == Fraction(0, 1)