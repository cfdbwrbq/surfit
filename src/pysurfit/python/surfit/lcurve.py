"""L-curve prototype for smoothing selection.

Unlike spatial CV, this uses one full solve per candidate and records data
misfit versus a roughness norm.  It is a heuristic corner finder, not GCV and
not a proof that the chosen smoothing is optimal.
"""

import numpy as np


def roughness(values, extent, order=2):
    """RMS of first or second finite differences over defined cells."""
    values = np.asarray(values, dtype=float)
    dx = float(extent["step_x"])
    dy = float(extent["step_y"])
    if order == 1:
        gx = np.diff(values, axis=1) / dx
        gy = np.diff(values, axis=0) / dy
        parts = [gx[np.isfinite(gx)], gy[np.isfinite(gy)]]
    elif order == 2:
        gx = (values[:, 2:] - 2.0 * values[:, 1:-1] + values[:, :-2]) / (dx * dx)
        gy = (values[2:, :] - 2.0 * values[1:-1, :] + values[:-2, :]) / (dy * dy)
        parts = [gx[np.isfinite(gx)], gy[np.isfinite(gy)]]
    else:
        raise ValueError("order must be 1 or 2")
    values = np.concatenate(parts)
    return float(np.sqrt(np.mean(values * values))) if values.size else float("nan")


def _corner(scores):
    misfit = np.array([score["misfit"] for score in scores], dtype=float)
    rough = np.array([score["roughness"] for score in scores], dtype=float)
    good = np.isfinite(misfit) & np.isfinite(rough)
    if good.sum() < 2:
        return 0
    indices = np.flatnonzero(good)
    x = (misfit[indices] - misfit[indices].min()) / (
        np.ptp(misfit[indices]) or 1.0)
    y = (rough[indices] - rough[indices].min()) / (
        np.ptp(rough[indices]) or 1.0)
    x0, y0 = x[0], y[0]
    x1, y1 = x[-1], y[-1]
    denominator = np.hypot(y1 - y0, x1 - x0)
    if denominator == 0:
        return int(indices[0])
    distances = np.abs((y1 - y0) * x - (x1 - x0) * y +
                       x1 * y0 - y1 * x0) / denominator
    return int(indices[int(np.argmax(distances))])


def select_parameter_lcurve(build, x, y, z, parameters, weights=None,
                            order=2, extent=None, holdout=0.25, seed=0):
    """Run one solve per parameter and choose the L-curve corner.

    ``build(parameter, train_indices, train_weights)`` must return a solved
    Session.  One deterministic holdout split is scored per parameter, so the
    data misfit is not zero as it is when training points are evaluated on
    themselves.  The returned scores are JSON-ready; this is a prototype, not
    GCV.
    """
    parameters = list(parameters)
    if not parameters:
        raise ValueError("parameters must not be empty")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    all_indices = np.arange(x.size)
    if not 0.0 < holdout < 1.0:
        raise ValueError("holdout must be between 0 and 1")
    rng = np.random.default_rng(seed)
    rng.shuffle(all_indices)
    split = max(1, int(round(x.size * (1.0 - holdout))))
    train = np.sort(all_indices[:split])
    test = np.sort(all_indices[split:])
    train_weights = None if weights is None else np.asarray(weights)[train]
    test_weights = None if weights is None else np.asarray(weights)[test]
    scores = []
    for parameter in parameters:
        task = build(parameter, train, train_weights)
        values = task.values()
        residual = task.residuals(x[test], y[test], z[test],
                                  weights=test_weights)
        task_extent = task.extent() if hasattr(task, "extent") else extent
        if task_extent is None:
            raise ValueError("pass extent= for tasks without extent()")
        scores.append({
            "parameter": parameter,
            "misfit": float(residual["rmse"]),
            "roughness": roughness(values, task_extent, order=order),
        })
        close = getattr(task, "close", None)
        if close is not None:
            close()
    corner = _corner(scores)
    return {
        "parameter": scores[corner]["parameter"],
        "method": "lcurve",
        "order": order,
        "corner": corner,
        "holdout": int(test.size),
        "scores": scores,
    }
