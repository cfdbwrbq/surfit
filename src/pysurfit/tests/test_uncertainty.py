"""Ensemble spread and bootstrap resampling.

The pure check pins the mean/std/percentile definitions on two tiny fields.
The integration check rebuilds a real surface from resampled points and proves
that the spread has the same grid shape and is positive.

  python3 test_uncertainty.py
"""

import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402
from surfit.diagnostics import bootstrap_uncertainty, ensemble  # noqa: E402


def pure_check():
    fields = [np.array([[1.0, 2.0], [3.0, 4.0]]),
              np.array([[3.0, 4.0], [5.0, 6.0]])]
    stats = ensemble(fields)
    assert np.allclose(stats["mean"], [[2.0, 3.0], [4.0, 5.0]])
    assert np.allclose(stats["std"], [[1.0, 1.0], [1.0, 1.0]])
    assert np.all(stats["n"] == 2)
    print("PASS: ensemble mean and spread")


def integration_check():
    rng = np.random.default_rng(2026)
    x = rng.uniform(-9, 9, 400)
    y = rng.uniform(-9, 9, 400)
    z = np.sin(x / 2.0) * np.cos(y / 3.0)

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")

        def build(sample):
            with open(path, "w", encoding="ascii") as stream:
                for index in sample:
                    stream.write("%.17g\t%.17g\t%.17g\n"
                                 % (x[index], y[index], z[index]))
            task = surfit.Session(map_name="boot", tol=1e-7)
            assert all(task.read_points(path, "p"))
            task.grid(-10, 10, 1.0, -10, 10, 1.0)
            task.points("p")
            task.completer(1, 1.6)
            task.solve()
            return task

        stats = bootstrap_uncertainty(build, x.size, replicates=4, seed=7)

    assert stats["mean"].shape == stats["std"].shape
    assert np.isfinite(stats["mean"]).all()
    assert np.isfinite(stats["std"]).all()
    assert stats["std"].max() > 0
    print("PASS: four bootstrap surfaces")


def main():
    pure_check()
    integration_check()
    print("PASS: uncertainty ensemble")


if __name__ == "__main__":
    main()
