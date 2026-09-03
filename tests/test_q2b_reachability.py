import pytest

from experiments.q2b_adapted.reachability import gate_b_verdict, sign_structure
from sim.thermal import adapted_optimum


def test_gate_b_window_spans_min_minus_to_max_plus_half_width():
    """The algal source reports TWO site values (5 and 7 C), so the window is
    [min-5, max+5], not +/-5 around a single number."""
    passed, lo, hi = gate_b_verdict(adapted_optimum(1.0, 4.0), [5.0, 7.0], 5.0)
    assert (lo, hi) == pytest.approx((0.0, 12.0))
    assert passed is True


def test_gate_b_fails_for_the_vascular_lamina():
    passed, lo, hi = gate_b_verdict(adapted_optimum(1.0, 2.0), [29.4], 5.0)
    assert (lo, hi) == pytest.approx((24.4, 34.4))
    assert passed is False
    # positive control in the same test: the algal case passes the same function
    assert gate_b_verdict(adapted_optimum(1.0, 4.0), [5.0, 7.0], 5.0)[0] is True


def test_gate_b_rejects_an_empty_measured_list():
    with pytest.raises(ValueError, match="measured"):
        gate_b_verdict(278.31, [], 5.0)
    assert gate_b_verdict(278.31, [5.0], 5.0)[1] == pytest.approx(0.0)


def test_sign_structure_reports_transitions_in_order():
    # monotone decreasing: exactly one positive->negative transition
    assert sign_structure(lambda r: 10.0 - r, 0.5, 100.0, 400) == [(1, -1)]
    # negative -> positive -> negative
    got = sign_structure(lambda r: -((r - 2.0) ** 2) + 1.0, 0.5, 100.0, 400)
    assert got == [(-1, 1), (1, -1)]
