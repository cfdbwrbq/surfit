"""Injection-recovery on fields whose truth is known.

Parity tests prove that Python and Tcl give the same answer.  They do not prove
that the answer is close to the field that generated the samples.  This test
does the second part:

  * build a known field on a grid;
  * sample it at scattered points;
  * solve from a training subset plus the completer;
  * compare the result with the truth at the cell centres and at the held-out
    points.

The thresholds are deliberately loose: this is a bias/scale check, not a
promise of the solver's absolute accuracy.  The printed RMSE and bias are the
numbers to watch when the solver, the rule order or the default tolerance
changes.

  python3 test_synthetic.py
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

STEP = 0.25
XMIN = YMIN = -10.0
XMAX = YMAX = 10.0
POINTS = 3000
TOL = 1e-7


def plane(x, y):
    return 1.0 + 0.25 * x - 0.15 * y


def gaussian(x, y):
    return 3.0 * np.exp(-((x - 2.0) ** 2 + (y + 1.0) ** 2) / (2.0 * 2.5 ** 2))


def sinusoid(x, y):
    return np.sin(x / 2.0) * np.cos(y / 3.0)


def sample_points(rng, field):
    x = rng.uniform(XMIN + 0.5, XMAX - 0.5, POINTS)
    y = rng.uniform(YMIN + 0.5, YMAX - 0.5, POINTS)
    return x, y, field(x, y)


def write_points(path, x, y, z):
    with open(path, "w", encoding="ascii") as stream:
        for xi, yi, zi in zip(x, y, z):
            stream.write("%.17g\t%.17g\t%.17g\n" % (xi, yi, zi))


def solve(path):
    task = surfit.Session(map_name="synthetic", tol=TOL)
    assert all(task.read_points(path, "p"))
    task.grid(XMIN, XMAX, STEP, YMIN, YMAX, STEP)
    task.points("p")
    task.completer(1, 1.6)
    task.solve()
    return task.values()


def cell_centres(values):
    height, width = values.shape
    x = XMIN + (np.arange(width) + 0.5) * STEP
    y = YMIN + (np.arange(height) + 0.5) * STEP
    return np.meshgrid(x, y)


def at_cells(values, x, y):
    """Nearest cell index for each sample point; the grid is cell-constant."""
    height, width = values.shape
    ix = np.clip(np.floor((x - XMIN) / STEP).astype(int), 0, width - 1)
    iy = np.clip(np.floor((y - YMIN) / STEP).astype(int), 0, height - 1)
    return values[iy, ix]


def check(name, field, seed, relative_limit, validation_limit):
    rng = np.random.default_rng(seed)
    x, y, z = sample_points(rng, field)
    train = np.arange(POINTS) < int(POINTS * 0.7)
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        write_points(path, x[train], y[train], z[train])
        values = solve(path)

    xx, yy = cell_centres(values)
    truth = field(xx, yy)
    defined = surfit.defined_mask(values)
    assert defined.sum() > 0, "%s: no defined cells" % name
    error = values[defined] - truth[defined]
    span = truth.max() - truth.min()
    rmse = float(np.sqrt(np.mean(error ** 2)))
    bias = float(np.mean(error))
    relative = rmse / span if span else rmse
    predicted = at_cells(values, x[~train], y[~train])
    validation = float(np.sqrt(np.mean((predicted - z[~train]) ** 2)))
    validation_relative = validation / span if span else validation
    print("%-9s rmse=%.6f bias=%+.6f rel=%.4f val=%.4f val_rel=%.4f"
          % (name, rmse, bias, relative, validation, validation_relative))
    assert abs(bias) <= relative_limit * span, "%s: biased" % name
    assert relative <= relative_limit, "%s: rmse %.4f > %.4f" % (
        name, relative, relative_limit)
    assert validation_relative <= validation_limit, (
        "%s: held-out rmse %.4f > %.4f" % (
            name, validation_relative, validation_limit))


def main():
    check("plane", plane, 11, 0.01, 0.02)
    check("gaussian", gaussian, 12, 0.08, 0.12)
    check("sinusoid", sinusoid, 13, 0.15, 0.20)
    print("PASS: every known field is recovered within its threshold")


if __name__ == "__main__":
    main()
