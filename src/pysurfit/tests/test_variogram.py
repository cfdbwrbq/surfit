"""Variogram diagnostics and the anisotropy suggestion.

These are diagnostics, not a kriging solver.  The synthetic checks use an
analytic spherical variogram for the fit and a field that varies mostly along
x for the direction check.

  python3 test_variogram.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def analytic_check():
    lag = np.arange(1.0, 11.0)
    range_ = 5.0
    ratio = np.clip(lag / range_, 0.0, 1.0)
    gamma = 0.1 + 2.0 * (1.0 - 1.5 * ratio + 0.5 * ratio ** 3)
    fit = surfit.fit_variogram(lag, gamma, model="spherical")
    assert abs(fit["range"] - range_) < 0.5, fit
    assert fit["nugget"] >= 0.0
    assert fit["sill"] > 0.0
    assert fit["rmse"] < 0.1
    print("PASS: spherical variogram fit")


def data_check():
    rng = np.random.default_rng(2026)
    x = rng.uniform(0.0, 20.0, 180)
    y = rng.uniform(0.0, 20.0, 180)
    z = np.sin(x / 2.0)
    experimental = surfit.experimental_variogram(x, y, z, bins=8,
                                                 max_lag=8.0)
    assert experimental["gamma"].size == 8
    assert np.any(experimental["count"] > 0)
    assert np.any(experimental["gamma"] > 0)
    directional = surfit.experimental_variogram(
        x, y, z, bins=6, max_lag=6.0, direction=90.0)
    assert directional["count"].sum() > 0
    result = surfit.anisotropy(
        x, y, z, angles=(0.0, 90.0), bins=8, max_lag=8.0)
    assert result["angle"] in (0.0, 90.0)
    assert result["ratio"] >= 1.0
    assert len(result["ranges"]) == 2
    assert result["skipped"] == []

    line_x = np.linspace(0.0, 10.0, 50)
    line_y = np.zeros_like(line_x)
    line_z = np.sin(line_x)
    partial = surfit.anisotropy(
        line_x, line_y, line_z, angles=(0.0, 90.0, 180.0),
        bins=8, max_lag=8.0)
    assert partial["skipped"], partial
    assert partial["skipped"][0]["direction"] == 90.0
    try:
        surfit.anisotropy(
            line_x, line_y, line_z, angles=(0.0, 90.0, 180.0),
            bins=8, max_lag=8.0, strict=True)
    except ValueError as error:
        assert "skipped" in str(error)
    else:
        raise AssertionError("strict anisotropy did not raise")
    print("PASS: experimental, directional and anisotropy diagnostics")


def main():
    analytic_check()
    data_check()
    print("PASS: variogram diagnostics")


if __name__ == "__main__":
    main()
