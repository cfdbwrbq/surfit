"""Physical invariants that do not compare against the Tcl front end."""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def solve(x, y, z, extent=(0.0, 1.0, 0.1, 0.0, 1.0, 0.1)):
    task = surfit.Session(map_name="physics", tol=1e-7)
    task.add_points(x, y, z, name="p")
    task.grid(*extent)
    task.points("p")
    task.completer(1, 1.6)
    task.solve()
    values = task.values().copy()
    task.close()
    return values


def data():
    rng = np.random.default_rng(17)
    x = rng.uniform(0.05, 0.95, 24)
    y = rng.uniform(0.05, 0.95, 24)
    z = np.sin(3.0 * x) + np.cos(4.0 * y) + 0.2 * x * y
    return x, y, z


def test_translation():
    x, y, z = data()
    base = solve(x, y, z)
    shifted = solve(x + 10.0, y - 20.0, z,
                    extent=(10.0, 11.0, 0.1, -20.0, -19.0, 0.1))
    assert np.allclose(base, shifted, rtol=1e-6, atol=1e-6)


def test_rotation_90():
    x, y, z = data()
    base = solve(x, y, z)
    # (x, y) -> (1-y, x) is a 90-degree rotation of the unit square.
    rotated = solve(1.0 - y, x, z)
    assert np.allclose(np.rot90(base, 3), rotated, rtol=1e-2, atol=2e-2)


def test_linear_field():
    gx, gy = np.meshgrid(np.arange(0.0, 1.01, 0.1),
                         np.arange(0.0, 1.01, 0.1))
    x = gx.ravel()
    y = gy.ravel()
    z = 2.0 * x - 3.0 * y + 7.0
    values = solve(x, y, z)
    expected = 2.0 * gx - 3.0 * gy + 7.0
    assert np.nanmax(np.abs(values - expected)) < 1e-5


def test_point_order():
    x, y, z = data()
    base = solve(x, y, z)
    order = np.random.default_rng(9).permutation(x.size)
    shuffled = solve(x[order], y[order], z[order])
    assert np.allclose(base, shuffled, rtol=1e-8, atol=1e-8)


def test_duplicate_points():
    x = np.array([0.2, 0.8, 0.2, 0.5])
    y = np.array([0.3, 0.7, 0.3, 0.5])
    z = np.array([1.0, 2.0, 1.0, 3.0])
    values = solve(x, y, z)
    assert np.isfinite(values).any()


def test_collinear_points():
    x = np.linspace(0.05, 0.95, 10)
    y = np.full(10, 0.5)
    z = np.linspace(1.0, 5.0, 10)
    values = solve(x, y, z)
    assert np.isfinite(values).any()


def main():
    test_translation()
    test_rotation_90()
    test_linear_field()
    test_point_order()
    test_duplicate_points()
    test_collinear_points()
    print("PASS: physics and invariance tests")


if __name__ == "__main__":
    main()
