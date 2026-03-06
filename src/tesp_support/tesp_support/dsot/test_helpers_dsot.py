import numpy as np

# python -m pytest .\tesp_support\dsot\test_helpers_dsot.py -q

from tesp_support.dsot.helpers_dsot import (
    Curve,
    build_isoelastic_bid_points,
    preference_to_elasticity,
    resample_curve,
    resample_curve_for_market,
    resample_curve_for_price_only,
)


def test_preference_to_elasticity_bounds():
    e0 = preference_to_elasticity(0.0, eps_min=0.05, eps_max=2.5)
    e1 = preference_to_elasticity(1.0, eps_min=0.05, eps_max=2.5)
    assert np.isclose(e0, 0.05)
    assert np.isclose(e1, 2.5)


def test_build_isoelastic_bid_points_monotone():
    bid = build_isoelastic_bid_points(
        preference=0.7,
        q_min_kw=0.0,
        q_ref_kw=4.0,
        q_max_kw=10.0,
        p_ref=0.12,
        price_cap=0.50,
        n_points=8,
    )
    q = np.array([pt[0] for pt in bid], dtype=float)
    p = np.array([pt[1] for pt in bid], dtype=float)

    # prices descend, quantities nondecreasing
    assert np.all(np.diff(p) <= 1e-12)
    assert np.all(np.diff(q) >= -1e-12)


def test_resample_curve_handles_unsorted_duplicates():
    x = [5.0, 1.0, 1.0, 3.0]
    y = [50.0, 10.0, 10.0, 30.0]
    xr, yr = resample_curve(x, y, min_q=1.0, max_q=5.0, num_samples=5)

    assert len(xr) == 5
    assert len(yr) == 5
    assert np.all(np.diff(np.array(xr)) >= 0)


def test_resample_curve_for_price_only():
    x1 = [0.0, 2.0, 4.0]
    x2 = [4.0, 0.0, 2.0]  # unsorted on purpose
    y2 = [0.40, 0.10, 0.20]
    yp = resample_curve_for_price_only(x1, x2, y2)
    assert len(yp) == len(x1)


def test_resample_curve_for_market_no_overlap():
    x, by, sy = resample_curve_for_market(
        [0.0, 1.0], [0.4, 0.3],
        [2.0, 3.0], [0.2, 0.1]
    )
    assert len(x) == 2
    assert len(by) == 2
    assert len(sy) == 2


def test_curve_aggregator_accepts_variable_points_buyer():
    c = Curve([0.50, 0.00], 21)
    bid = [
        [0.5, 0.50],
        [1.0, 0.40],
        [2.0, 0.30],
        [3.5, 0.20],
        [5.0, 0.10],
        [6.0, 0.05],
        [6.5, 0.02],
        [7.0, 0.00],
    ]
    c.curve_aggregator("Buyer", bid)

    assert len(c.quantities) == 21
    # as prices decrease along the sampled curve, buyer quantity should be nondecreasing
    assert np.all(np.diff(c.quantities) >= -1e-9)


def test_curve_aggregator_accepts_variable_points_seller():
    c = Curve(0.50, 21)
    bid = [
        [0.0, 0.00],
        [1.0, 0.10],
        [2.0, 0.20],
        [4.0, 0.30],
        [6.0, 0.40],
        [8.0, 0.50],
    ]
    c.curve_aggregator("Seller", bid)
    assert len(c.quantities) == 21