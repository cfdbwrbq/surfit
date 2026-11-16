"""Parallel CV, bootstrap and ensemble builders match the serial paths."""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402

RNG = np.random.default_rng(31)
X = RNG.uniform(0, 1, 18)
Y = RNG.uniform(0, 1, 18)
Z = 2 * X + 3 * Y


def build(indices, weights):
    task = surfit.Session(map_name="parallel", tol=1e-7)
    task.add_points(X[indices], Y[indices], Z[indices], weights=weights,
                    name="p")
    task.grid(0, 1, 0.1, 0, 1, 0.1)
    task.points("p")
    task.completer(1, 1.6)
    task.solve()
    return task


def stack_builder(value):
    def build_stack():
        stack = surfit.SurfaceStack("parallel-%s" % value)
        stack.add_layer("top", lambda: layer(value))
        stack.solve()
        return stack
    return build_stack


def layer(value):
    task = surfit.Session(map_name="layer", tol=1e-7)
    task.add_points([0, 1, 0, 1], [0, 0, 1, 1], [value] * 4, name="p")
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    serial = surfit.cross_validate(build, X, Y, Z, folds=3, n_jobs=1)
    parallel = surfit.cross_validate(build, X, Y, Z, folds=3, n_jobs=2)
    assert np.allclose(serial["rmse"], parallel["rmse"], rtol=1e-10)
    assert len(serial["fold_details"]) == len(parallel["fold_details"])

    serial_boot = surfit.bootstrap_uncertainty(
        lambda sample: build(sample, None), 12, replicates=4, seed=7)
    parallel_boot = surfit.bootstrap_uncertainty(
        lambda sample: build(sample, None), 12, replicates=4, seed=7,
        n_jobs=2)
    assert np.allclose(serial_boot["mean"], parallel_boot["mean"])

    serial_ens = surfit.SurfaceEnsemble.from_builders(
        [stack_builder(1.0), stack_builder(2.0)], workers=1)
    parallel_ens = surfit.SurfaceEnsemble.from_builders(
        [stack_builder(1.0), stack_builder(2.0)], workers=2)
    assert np.allclose(serial_ens["top"], parallel_ens["top"])
    print("PASS: parallel CV, bootstrap and ensemble builders")


if __name__ == "__main__":
    main()
