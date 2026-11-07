"""K-fold cross-validation on a known field.

Injection-recovery in ``test_synthetic.py`` has a fixed 70/30 split.  This test
rotates the held-out quarter, so every point is predicted by a surface that did
not see it.  It is still a synthetic field, but it is the closest cheap proxy
for a geoscience "blind well" check.

  python3 test_cross_validation.py
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
from surfit.diagnostics import point_residuals  # noqa: E402

POINTS = 1200
FOLDS = 4
STEP = 0.5
XMIN = YMIN = -10.0
XMAX = YMAX = 10.0


def field(x, y):
    return 2.0 * np.exp(-((x - 1.0) ** 2 + (y + 2.0) ** 2) / (2.0 * 3.0 ** 2))


def solve(path):
    task = surfit.Session(map_name="cv", tol=1e-7)
    assert all(task.read_points(path, "p"))
    task.grid(XMIN, XMAX, STEP, YMIN, YMAX, STEP)
    task.points("p")
    task.completer(1, 1.6)
    task.solve()
    return task.values(), surfit._surfit.surf_extent(0)


def main():
    rng = np.random.default_rng(2026)
    x = rng.uniform(XMIN + 0.5, XMAX - 0.5, POINTS)
    y = rng.uniform(YMIN + 0.5, YMAX - 0.5, POINTS)
    z = field(x, y)
    span = float(field(x, y).ptp()) if hasattr(z, "ptp") else float(np.ptp(z))
    fold = np.arange(POINTS) % FOLDS

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "train.txt")
        scores = []
        for number in range(FOLDS):
            train = fold != number
            validation = ~train
            with open(path, "w", encoding="ascii") as stream:
                for xi, yi, zi in zip(x[train], y[train], z[train]):
                    stream.write("%.17g\t%.17g\t%.17g\n" % (xi, yi, zi))
            values, extent = solve(path)
            stats = point_residuals(values, extent, x[validation],
                                    y[validation], z[validation])
            assert stats["n"] == int(validation.sum()), stats
            scores.append(stats["rmse"])
            print("fold %d: n=%d rmse=%.6f" % (number, stats["n"], stats["rmse"]))

    mean_rmse = float(np.mean(scores))
    print("mean held-out rmse=%.6f span=%.3f" % (mean_rmse, span))
    assert mean_rmse / span < 0.15, "cross-validation error is too large"
    print("PASS: four-fold cross-validation")


if __name__ == "__main__":
    main()
