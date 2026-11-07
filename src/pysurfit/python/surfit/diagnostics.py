"""Residual diagnostics for a solved surface.

The engine returns one surface and no covariance.  These helpers do not invent
an error model; they report what the data actually say about the result:

* residual at each sample: observed minus the value of its grid cell;
* unweighted RMSE and bias;
* weighted MSE, and ``chi2`` if the weights are inverse variances.

A point is skipped when its cell is outside the grid or undefined.  The grid is
cell-constant, so the prediction is the cell value, not a bilinear
interpolation.
"""

import numpy as np

from surfit import _surfit as _core

_UNDEF = float(np.finfo(np.float32).max)


def _defined(values):
    return ~np.isclose(values, _UNDEF, rtol=1e-6)


def _extent(extent):
    """Accept the dict from ``surf_extent`` with the fields we need."""
    required = ("min_x", "min_y", "step_x", "step_y", "count_x", "count_y")
    missing = [name for name in required if name not in extent]
    if missing:
        raise ValueError("extent is missing: %s" % ", ".join(missing))
    return extent


def point_residuals(values, extent, x, y, z, weights=None):
    """Residuals of sample points against a cell-constant surface.

    ``values`` is a ``(count_y, count_x)`` array; ``extent`` is the dict
    returned by ``surf_extent``.  ``x``, ``y`` and ``z`` are equal-length
    sequences.  ``weights`` is optional and has one positive value per point;
    a zero weight drops the point from the statistics.

    Returns a dict with ``n``, ``residuals``, ``rmse``, ``bias``,
    ``weighted_mse``, ``chi2`` and ``dof``.  With inverse-variance weights,
    ``chi2`` is the usual sum of weighted squared residuals.
    """
    values = np.asarray(values, dtype=float)
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    z = np.asarray(z, dtype=float).ravel()
    if not (x.size == y.size == z.size):
        raise ValueError("x, y and z must have the same length")
    if weights is None:
        weights = np.ones(x.size, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float).ravel()
        if weights.size != x.size:
            raise ValueError("weights must have one value per point")

    extent = _extent(extent)
    col = np.rint((x - extent["min_x"]) / extent["step_x"]).astype(int)
    row = np.rint((y - extent["min_y"]) / extent["step_y"]).astype(int)
    inside = ((col >= 0) & (col < extent["count_x"]) &
              (row >= 0) & (row < extent["count_y"]))
    predicted = np.full(x.shape, np.nan)
    predicted[inside] = values[row[inside], col[inside]]
    usable = inside & _defined(predicted) & np.isfinite(z) & (weights > 0)
    residual = z - predicted
    used = residual[usable]
    used_weights = weights[usable]
    n = int(used.size)
    if n == 0:
        return {
            "n": 0,
            "residuals": used,
            "predicted": predicted,
            "used": usable,
            "rmse": float("nan"),
            "bias": float("nan"),
            "weighted_mse": float("nan"),
            "chi2": float("nan"),
            "dof": 0,
        }

    weight_sum = used_weights.sum()
    weighted_sse = float(np.sum(used_weights * used * used))
    return {
        "n": n,
        "residuals": used,
        "predicted": predicted,
        "used": usable,
        "rmse": float(np.sqrt(np.mean(used * used))),
        "bias": float(np.mean(used)),
        "weighted_mse": weighted_sse / weight_sum,
        "chi2": weighted_sse,
        "dof": n - 1,
    }


def outlier_mask(values, extent, x, y, z, weights=None, threshold=3.5):
    """Flags points whose residual is far from the residual median.

    Uses the median absolute deviation (MAD), scaled to sigma.  A point is
    flagged when ``|r - median(r)| > threshold * 1.4826 * MAD``.  Fewer than
    three usable points produce no flags.

    Returns ``(flags, stats)``; ``flags`` has one boolean per input point.
    A flag is a suggestion, not a robust loss: drop or down-weight the point
    yourself and re-solve.
    """
    stats = point_residuals(values, extent, x, y, z, weights)
    flags = np.zeros(np.asarray(x).size, dtype=bool)
    residuals = stats["residuals"]
    if residuals.size < 3:
        return flags, stats
    median = float(np.median(residuals))
    mad = float(np.median(np.abs(residuals - median)))
    sigma = 1.4826 * mad
    if sigma > 0:
        flags[stats["used"]] = np.abs(residuals - median) > threshold * sigma
    return flags, stats


def _session_outliers(task, x, y, z, weights, surface, threshold):
    position = _position(task, surface)
    if position < 0:
        raise KeyError("no surface matches %r" % (surface,))
    return outlier_mask(task.values(surface), _core.surf_extent(position),
                        x, y, z, weights, threshold)


def robust_weights(residuals, scale=None, loss="huber", tuning=None):
    """Return IRLS weights for a robust loss.

    ``loss="huber"`` uses the Huber weight and ``"tukey"`` the Tukey biweight.
    ``scale`` is the residual scale; by default it is ``1.4826 * MAD``.  A
    point with a small residual keeps weight 1; a large one is down-weighted
    (Huber) or zeroed (Tukey).

    This is the weighting step, not a solver.  Rebuild the task with these
    weights and solve again; repeat a few times.  The engine still minimizes
    least squares inside each iteration.
    """
    residuals = np.asarray(residuals, dtype=float)
    if scale is None:
        centre = float(np.median(residuals)) if residuals.size else 0.0
        scale = 1.4826 * float(np.median(np.abs(residuals - centre)))
    if not scale or scale <= 0:
        return np.ones(residuals.shape, dtype=float)
    if loss == "huber":
        cutoff = 1.345 if tuning is None else tuning
        values = np.abs(residuals) / scale
        return np.where(values <= cutoff, 1.0, cutoff / np.maximum(values, 1e-300))
    if loss == "tukey":
        cutoff = 4.685 if tuning is None else tuning
        values = np.abs(residuals) / scale
        inner = np.maximum(1.0 - (values / cutoff) ** 2, 0.0)
        return inner ** 2
    raise ValueError("unknown robust loss %r" % (loss,))


def ensemble(fields):
    """Mean, spread and percentiles of several surface arrays.

    Each field is a ``(count_y, count_x)`` array.  Undefined nodes are ignored
    per cell; ``n`` reports how many fields were defined there.  This is an
    ensemble spread, not a covariance or a posterior.
    """
    arrays = [np.asarray(field, dtype=float) for field in fields]
    if not arrays:
        raise ValueError("ensemble needs at least one field")
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all fields in an ensemble must have the same shape")
    stack = np.stack(arrays)
    stack = np.where(_defined(stack), stack, np.nan)
    count = np.sum(~np.isnan(stack), axis=0)
    return {
        "mean": np.nanmean(stack, axis=0),
        "std": np.nanstd(stack, axis=0),
        "p05": np.nanpercentile(stack, 5, axis=0),
        "p95": np.nanpercentile(stack, 95, axis=0),
        "n": count,
        "fields": stack,
    }


def bootstrap_uncertainty(build, count, replicates=100, seed=0):
    """Resample ``count`` point indices and collect the resulting surfaces.

    ``build(sample)`` must return a solved task or a surface array.  The helper
    draws ``count`` indices with replacement for each replicate, so the caller
    can rebuild the points from ``sample``.  The model is fixed; only the
    sampled data vary.
    """
    if count <= 0:
        raise ValueError("count must be positive")
    if replicates < 2:
        raise ValueError("replicates must be at least 2")
    rng = np.random.default_rng(seed)
    fields = []
    for iteration in range(replicates):
        sample = rng.integers(0, count, count)
        result = build(sample)
        if hasattr(result, "values"):
            result = result.values()
        fields.append(np.asarray(result, dtype=float))
    return ensemble(fields)


def _position(task, surface):
    if surface is None:
        return _core.surf_count() - 1
    return task.surf_index(surface)


def _session_residuals(task, x, y, z, weights, surface):
    position = _position(task, surface)
    if position < 0:
        raise KeyError("no surface matches %r" % (surface,))
    values = task.values(surface)
    extent = _core.surf_extent(position)
    return point_residuals(values, extent, x, y, z, weights)
