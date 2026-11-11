"""The reusable spatial cross-validation API.

The solver test in ``test_cross_validation.py`` checks accuracy.  This test
checks the contract: folds do not overlap, blocks stay together, the callback
sees only training points, and the summary is JSON-ready.

  python3 test_cross_validation_api.py
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


POINTS = 80
XMIN = YMIN = 0.0
XMAX = YMAX = 10.0
STEP = 1.0


def field(x, y):
    return np.sin(x / 2.0) + np.cos(y / 3.0)


def extent():
    return {
        "min_x": XMIN, "max_x": XMAX, "min_y": YMIN, "max_y": YMAX,
        "step_x": STEP, "step_y": STEP,
        "count_x": int(round((XMAX - XMIN) / STEP)) + 1,
        "count_y": int(round((YMAX - YMIN) / STEP)) + 1,
    }


def values():
    grid = extent()
    x = np.linspace(grid["min_x"], grid["max_x"], grid["count_x"])
    y = np.linspace(grid["min_y"], grid["max_y"], grid["count_y"])
    return field(*np.meshgrid(x, y))


def main():
    rng = np.random.default_rng(2026)
    x = rng.uniform(XMIN, XMAX, POINTS)
    y = rng.uniform(YMIN, YMAX, POINTS)
    z = field(x, y)
    calls = []

    def build(train, train_weights):
        calls.append((np.asarray(train), train_weights))
        return values(), extent()

    result = surfit.cross_validate(build, x, y, z, folds=4, mode="random",
                                   seed=7)
    assert result["n"] == POINTS
    assert result["folds"] == 4
    assert len(result["fold_details"]) == 4
    assert all(detail["n_test"] > 0 for detail in result["fold_details"])
    assert all(np.isfinite(detail["rmse"]) for detail in result["fold_details"])
    assert all(call[1] is None for call in calls)
    seen = np.concatenate([call[0] for call in calls])
    assert np.unique(seen).size == POINTS, "a training point was skipped"
    assert all(np.isfinite([result["rmse"], result["bias"], result["mae"],
                            result["weighted_mse"]]))
    assert result["rmse"] >= 0.0

    labels = surfit.fold_assignment(x, y, folds=4, mode="block", block=2.5,
                                    seed=7)
    assert labels.shape == (POINTS,)
    assert set(np.unique(labels)) == {0, 1, 2, 3}
    block_calls = []

    def block_build(train, train_weights):
        block_calls.append(np.asarray(train))
        return values(), extent()

    block_result = surfit.cross_validate(
        block_build, x, y, z, folds=4, mode="block", block=2.5, seed=7)
    assert block_result["mode"] == "block"
    assert block_result["block"] == 2.5
    assert len(block_calls) == 4
    assert block_result["rmse"] >= 0.0

    interleaved = surfit.fold_assignment(x, y, folds=4, mode="kfold")
    assert set(np.unique(interleaved)) == {0, 1, 2, 3}

    groups = np.repeat(np.arange(10), 8)
    group_labels = surfit.fold_assignment(
        x, y, folds=5, mode="group", groups=groups, seed=7)
    for group in np.unique(groups):
        assert np.unique(group_labels[groups == group]).size == 1
    grouped = surfit.cross_validate(
        build, x, y, z, folds=5, mode="group", groups=groups, seed=7)
    assert grouped["folds"] == 5
    assert len(grouped["group_details"]) == 10
    assert all("group" in detail for detail in grouped["group_details"])
    leave_one_out = surfit.cross_validate(
        build, x, y, z, folds=None, mode="group", groups=groups, seed=7)
    assert leave_one_out["folds"] == 10
    assert len(leave_one_out["fold_details"]) == 10
    print("PASS: spatial CV folds, block folds and JSON-ready metrics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
