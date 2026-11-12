"""L-curve prototype on one deterministic holdout split."""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    rng = np.random.default_rng(3)
    x = rng.uniform(0, 1, 20)
    y = rng.uniform(0, 1, 20)
    z = 2.0 * x + 3.0 * y + rng.normal(0, 0.05, 20)
    extent = {"min_x": 0, "min_y": 0, "step_x": 1 / 15, "step_y": 1 / 15}

    def build(parameter, train, weights):
        task = surfit.Session(map_name="lcurve", tol=1e-7)
        task.add_points(x[train], y[train], z[train], weights=weights,
                        name="p")
        task.grid(0, 1, 1 / 15, 0, 1, 1 / 15)
        task.points("p")
        task.completer(1, parameter)
        task.solve()
        return task

    result = surfit.select_parameter_lcurve(
        build, x, y, z, [0.5, 1.0, 2.0], extent=extent, holdout=0.25)
    assert result["method"] == "lcurve"
    assert result["holdout"] == 5
    assert len(result["scores"]) == 3
    assert all(score["misfit"] >= 0 for score in result["scores"])
    assert surfit.roughness(np.eye(3), extent) >= 0

    print("PASS: L-curve holdout prototype")


if __name__ == "__main__":
    main()
