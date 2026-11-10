"""Run a small task and inspect it instead of trusting one number.

    python3 examples/python/quality_workflow.py

The workflow is deliberately split into independent checks:

* residuals against the samples;
* spatial CV, where the validation points were not used to build the fold;
* a variogram fit and an anisotropy suggestion;
* per-node support and a typed diagnostics file;
* a quality report with provenance and source hashes.

The data are synthetic so the example runs anywhere.  It is a workflow, not a
claim that any one number is an uncertainty.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import numpy as np  # noqa: E402

import surfit  # noqa: E402

X0 = Y0 = -8.0
X1 = Y1 = 8.0
STEP = 1.0


def field(x, y):
    return (12.0 + 0.4 * x - 0.2 * y
            + 3.0 * np.exp(-((x - 1.0) ** 2 + (y + 2.0) ** 2) / 18.0))


def solve_task(path, indices=None, weights=None):
    """Build and solve the task, optionally from a subset of the samples."""
    task = surfit.Session(map_name="quality", tol=1e-7)
    if indices is None:
        assert all(task.read_points(path, "p", weights=weights))
    else:
        subset = path + ".train"
        data = np.loadtxt(path)
        np.savetxt(subset, data[indices], fmt="%.17g")
        assert all(task.read_points(
            subset, "p",
            weights=None if weights is None else weights[indices]))
    task.grid(X0, X1, STEP, Y0, Y1, STEP)
    task.points("p")
    task.completer(1, 1.6)
    task.solve()
    return task


def main():
    rng = np.random.default_rng(2026)
    x = rng.uniform(X0 + 0.5, X1 - 0.5, 180)
    y = rng.uniform(Y0 + 0.5, Y1 - 0.5, 180)
    z = field(x, y) + rng.normal(0.0, 0.15, x.size)

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        with open(path, "w", encoding="ascii") as stream:
            for xi, yi, zi in zip(x, y, z):
                stream.write("%.17g\t%.17g\t%.17g\n" % (xi, yi, zi))

        task = solve_task(path)
        values = task.values()
        residuals = task.residuals(x, y, z)
        report = task.report(x, y, z, sources=[path])
        diagnostics = task.diagnostic_points(x, y, z)
        support = task.quality_attributes(x, y, weights=None)

        variogram = surfit.experimental_variogram(x, y, z, bins=12)
        fit = surfit.fit_variogram(
            variogram["lag"], variogram["gamma"], model="spherical")
        direction = surfit.anisotropy(
            x, y, z, angles=(0, 45, 90, 135), bins=8)

        def build(train, train_weights):
            return solve_task(path, train, train_weights)

        cv = surfit.cross_validate(
            build, x, y, z, folds=4, mode="block", block=4.0)

        reduced = surfit.decluster_points(
            x, y, z, block=2.0, method="mean")
        extent = {
            "min_x": X0, "max_x": X1, "min_y": Y0, "max_y": Y1,
            "step_x": STEP, "step_y": STEP,
            "count_x": int(round((X1 - X0) / STEP)) + 1,
            "count_y": int(round((Y1 - Y0) / STEP)) + 1,
        }
        resolution = surfit.resolution_report(
            extent, x=x, y=y, values=values)

    print("grid          : %s defined=%d" % (
        values.shape, int(surfit.defined_mask(values).sum())))
    print("residuals     : n=%d rmse=%.3f bias=%.3f" % (
        residuals["n"], residuals["rmse"], residuals["bias"]))
    print("spatial CV    : rmse=%.3f mode=%s" % (
        cv["rmse"], cv["mode"]))
    print("variogram     : range=%.2f nugget=%.2f sill=%.2f" % (
        fit["range"], fit["nugget"], fit["sill"]))
    print("anisotropy    : angle=%.1f ratio=%.2f" % (
        direction["angle"], direction["ratio"]))
    print("support       : covered=%d uncovered=%d" % (
        report["grid"]["covered"], report["grid"]["uncovered"]))
    print("decluster     : %d -> %d points" % (x.size, reduced["x"].size))
    print("diagnostics   : used=%d outlier=%d" % (
        int(np.sum(diagnostics["code"] == 0)),
        int(np.sum(diagnostics["code"] == 1))))
    print("resolution    : nyquist=%.2f samples/cell=%.3f" % (
        resolution["nyquist"], resolution["samples_per_cell"]))
    print("provenance    : %s, sources=%d" % (
        report["provenance"]["engine_version"],
        len(report["provenance"]["sources"])))
    print("support array : %s" % (support["count"].shape,))


if __name__ == "__main__":
    main()
