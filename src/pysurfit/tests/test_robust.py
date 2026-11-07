"""The outer IRLS driver down-weights an outlier after several solves.

Twenty-one points share one grid cell: twenty measure 0 and one measures 100.
The unweighted mean is 100/21.  ``robust_solve`` rebuilds the task with Huber
weights, so the final cell should move towards 0 without changing the rule set.

  python3 test_robust.py
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
from surfit.diagnostics import robust_solve  # noqa: E402


def main():
    count = 21
    offset = np.arange(count) * 0.001
    x = 0.01 + offset
    y = 0.01 + offset
    z = np.zeros(count)
    z[-1] = 100.0

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")

        def build(weights):
            with open(path, "w", encoding="ascii") as stream:
                for xi, yi, zi, wi in zip(x, y, z, weights):
                    stream.write("%.17g\t%.17g\t%.17g\n" % (xi, yi, zi))
            task = surfit.Session(map_name="robust", tol=1e-9)
            assert all(task.read_points(path, "p", weights=list(weights)))
            task.grid(0, 1, 1, 0, 1, 1)
            task.points("p")
            task.solve()
            return task

        result = robust_solve(build, x, y, z, iterations=4, loss="huber")
        final = result["task"].values()
        defined = surfit.defined_mask(final)
        value = float(final[defined][0])

    print("initial mean=%.6f final=%.6f" % (z.mean(), value))
    assert value < 5.0, "Huber did not down-weight the outlier: %.6f" % value
    assert result["weights"][-1] < 0.5, result["weights"]
    print("PASS: robust IRLS moved the cell towards the inliers")


if __name__ == "__main__":
    main()
