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
from surfit.provenance import build_provenance

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


def cell_attributes(values, extent, x, y, weights=None):
    """Per-node data support for a solved grid.

    Returns arrays on the grid shape: ``count`` (samples in the cell),
    ``sum_weights``, ``negative_weights`` (sum of weights below zero),
    ``min_distance`` and ``mean_distance`` to the cell centre.  Distances are in
    the grid's coordinate units.  These are support diagnostics, not an error
    model; ``min_distance`` is NaN where a cell has no sample.
    """
    values = np.asarray(values, dtype=float)
    extent = _extent(extent)
    shape = (int(extent["count_y"]), int(extent["count_x"]))
    if values.shape != shape:
        raise ValueError("values shape does not match extent")
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if x.size != y.size:
        raise ValueError("x and y must have the same length")
    if weights is None:
        weights = np.ones(x.size, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float).ravel()
        if weights.size != x.size:
            raise ValueError("weights must have one value per point")
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights)
    col = np.floor((x[finite] - extent["min_x"]) / extent["step_x"]).astype(int)
    row = np.floor((y[finite] - extent["min_y"]) / extent["step_y"]).astype(int)
    inside = ((col >= 0) & (col < shape[1]) &
              (row >= 0) & (row < shape[0]))
    col = col[inside]
    row = row[inside]
    used_weights = weights[finite][inside]
    index = row * shape[1] + col
    size = shape[0] * shape[1]
    count = np.bincount(index, minlength=size).astype(int)
    sum_weights = np.bincount(index, weights=used_weights, minlength=size)
    negative = np.bincount(index, weights=np.minimum(used_weights, 0.0),
                           minlength=size)
    centre_x = extent["min_x"] + col * extent["step_x"]
    centre_y = extent["min_y"] + row * extent["step_y"]
    distance = np.hypot(x[finite][inside] - centre_x,
                        y[finite][inside] - centre_y)
    minimum = np.full(size, np.inf)
    np.minimum.at(minimum, index, distance)
    sum_distance = np.bincount(index, weights=distance, minlength=size)
    mean_distance = np.full(size, np.nan)
    covered = count > 0
    mean_distance[covered] = sum_distance[covered] / count[covered]
    minimum[~covered] = np.nan
    reshape = shape
    return {
        "count": count.reshape(reshape),
        "sum_weights": sum_weights.reshape(reshape),
        "negative_weights": negative.reshape(reshape),
        "min_distance": minimum.reshape(reshape),
        "mean_distance": mean_distance.reshape(reshape),
    }


#: Diagnostic point classes used by :func:`diagnostic_points`.
DIAGNOSTIC_CODES = {
    0: "used",
    1: "outlier",
    2: "undefined_cell",
    3: "outside_grid",
    4: "zero_weight",
}


def diagnostic_points(values, extent, x, y, z, weights=None, threshold=3.5):
    """Return point records with a typed diagnostic code.

    Every input point gets ``code``: 0 used, 1 outlier, 2 undefined cell,
    3 outside the grid, 4 zero weight.  ``residual`` and ``predicted`` are NaN
    when the point cannot be evaluated.  ``scale`` is the local cell size
    (grid diagonal divided by the square root of the sample count), so
    ``scaled_residual`` compares a residual with the support in that cell.
    """
    values = np.asarray(values, dtype=float)
    extent = _extent(extent)
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
    columns = np.rint((x - extent["min_x"]) / extent["step_x"]).astype(int)
    rows = np.rint((y - extent["min_y"]) / extent["step_y"]).astype(int)
    inside = ((columns >= 0) & (columns < extent["count_x"]) &
              (rows >= 0) & (rows < extent["count_y"]))
    predicted = np.full(x.shape, np.nan)
    predicted[inside] = values[rows[inside], columns[inside]]
    defined = inside & _defined(predicted)
    usable = defined & np.isfinite(z) & np.isfinite(weights) & (weights > 0)
    residual = np.full(x.shape, np.nan)
    residual[usable] = z[usable] - predicted[usable]
    flags, _ = outlier_mask(values, extent, x, y, z, weights, threshold)
    codes = np.zeros(x.size, dtype=int)
    codes[~inside] = 3
    codes[inside & ~defined] = 2
    codes[defined & (weights <= 0)] = 4
    codes[usable & flags] = 1
    support = cell_attributes(values, extent, x, y)
    safe_columns = np.clip(columns, 0, extent["count_x"] - 1)
    safe_rows = np.clip(rows, 0, extent["count_y"] - 1)
    count = support["count"][safe_rows, safe_columns].astype(float)
    diagonal = np.hypot(extent["step_x"], extent["step_y"])
    scale = np.full(x.shape, np.nan)
    scale[inside & (count > 0)] = diagonal / np.sqrt(count[inside & (count > 0)])
    scaled = np.abs(residual) / scale
    return {
        "x": x,
        "y": y,
        "z": z,
        "weights": weights,
        "predicted": predicted,
        "residual": residual,
        "scale": scale,
        "scaled_residual": scaled,
        "code": codes,
        "code_name": np.array([DIAGNOSTIC_CODES[int(code)] for code in codes]),
    }


def _json_number(value):
    return None if not np.isfinite(value) else float(value)


def diagnostics_to_geojson(document):
    """Convert :func:`diagnostic_points` output to a GeoJSON FeatureCollection."""
    features = []
    for index in range(document["x"].size):
        code = int(document["code"][index])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [_json_number(document["x"][index]),
                                         _json_number(document["y"][index])]},
            "properties": {
                "z": _json_number(document["z"][index]),
                "predicted": _json_number(document["predicted"][index]),
                "residual": _json_number(document["residual"][index]),
                "weight": _json_number(document["weights"][index]),
                "scale": _json_number(document["scale"][index]),
                "scaled_residual": _json_number(
                    document["scaled_residual"][index]),
                "code": code,
                "code_name": DIAGNOSTIC_CODES[code],
            },
        })
    return {"type": "FeatureCollection", "features": features}


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
            # Four equal inliers and one outlier give MAD=0.  Fall back to the
            # standard deviation so the outlier is still visible.
            scale = float(np.std(residuals))
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


def bootstrap_uncertainty(build, count, replicates=100, seed=0, blocks=None,
                          block_size=None, x=None, y=None):
    """Resample point indices and collect the resulting surfaces.

    ``build(sample)`` must return a solved task or a surface array.  By default
    indices are drawn independently (i.i.d.); pass ``blocks`` labels, or
    ``x``/``y`` plus ``block_size``, to resample whole spatial blocks.  Block
    bootstrap preserves the dependence that i.i.d. resampling breaks.

    The model is fixed; only the sampled data vary.  The result is ensemble
    spread, not a posterior.
    """
    if count <= 0:
        raise ValueError("count must be positive")
    if replicates < 2:
        raise ValueError("replicates must be at least 2")
    if blocks is not None and block_size is not None:
        raise ValueError("pass blocks or block_size, not both")
    if blocks is None and block_size is not None:
        if x is None or y is None:
            raise ValueError("block_size needs x and y")
        from surfit.cross_validation import block_labels
        blocks = block_labels(x, y, block_size)
    if blocks is not None:
        blocks = np.asarray(blocks).ravel()
        if blocks.size != count:
            raise ValueError("blocks must have one value per point")
        groups = [np.flatnonzero(blocks == value)
                  for value in np.unique(blocks)]
        groups = [group for group in groups if group.size]
        if not groups:
            raise ValueError("blocks must contain at least one point")
    else:
        groups = None
    rng = np.random.default_rng(seed)
    fields = []
    for iteration in range(replicates):
        if groups is None:
            sample = rng.integers(0, count, count)
        else:
            selected = rng.integers(0, len(groups), len(groups))
            sample = np.concatenate([groups[index] for index in selected])
        result = build(sample)
        if hasattr(result, "values"):
            result = result.values()
        fields.append(np.asarray(result, dtype=float))
    result = ensemble(fields)
    result["sampling"] = "block" if groups is not None else "iid"
    result["blocks"] = len(groups) if groups is not None else None
    return result


def robust_solve(build, x, y, z, weights=None, loss="huber", iterations=4,
                  scale=None):
    """Run IRLS around a task builder.

    ``build(weights)`` must create and solve a task with those point weights.
    The driver solves, estimates residuals, updates the weights with the
    selected robust loss and repeats.  The model and the rules stay fixed; only
    the point weights change.

    Returns ``{"task": final_task, "weights": weights, "stats": stats,
    "iterations": iterations}``.  This is an outer IRLS loop: the engine's
    inner solve is still least squares.
    """
    if iterations < 1:
        raise ValueError("iterations must be positive")
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    z = np.asarray(z, dtype=float).ravel()
    if not (x.size == y.size == z.size):
        raise ValueError("x, y and z must have the same length")
    if weights is None:
        base = np.ones(x.size, dtype=float)
    else:
        base = np.asarray(weights, dtype=float).ravel()
        if base.size != x.size:
            raise ValueError("weights must have one value per point")
    current = base.copy()
    task = None
    stats = None
    for _ in range(iterations):
        task = build(current)
        if not hasattr(task, "residuals"):
            raise TypeError("build() must return a task with residuals()")
        stats = task.residuals(x, y, z, weights=current)
        if stats["n"] == 0:
            break
        correction = robust_weights(stats["residuals"], scale=scale, loss=loss)
        current[stats["used"]] = base[stats["used"]] * correction
    task = build(current)
    stats = task.residuals(x, y, z, weights=current)
    return {"task": task, "weights": current, "stats": stats,
            "iterations": iterations}


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

def quality_report(task, x, y, z, weights=None, surface=None, threshold=3.5,
                   sources=None):
    """Build a JSON-ready quality report for a solved surface.

    The report is deliberately a summary, not the full covariance: grid
    extent, residuals, outlier flags, point counts and provenance metadata.
    ``sources`` is an optional path or path -> SHA-256 mapping; the paths are
    recorded as given, so pass relative names if the report will be published.
    """
    position = _position(task, surface)
    if position < 0:
        raise KeyError("no surface matches %r" % (surface,))
    values = task.values(surface)
    extent = _core.surf_extent(position)
    stats = point_residuals(values, extent, x, y, z, weights)
    flags, _ = outlier_mask(values, extent, x, y, z, weights, threshold)
    defined = _defined(values)
    attributes = cell_attributes(values, extent, x, y, weights)
    covered = attributes["count"] > 0
    metadata = task.metadata
    return {
        "map_name": getattr(task, "_map_name", None),
        "surface": task.surf_names()[position],
        "grid": {
            "count_x": int(extent["count_x"]),
            "count_y": int(extent["count_y"]),
            "min_x": float(extent["min_x"]),
            "max_x": float(extent["max_x"]),
            "min_y": float(extent["min_y"]),
            "max_y": float(extent["max_y"]),
            "step_x": float(extent["step_x"]),
            "step_y": float(extent["step_y"]),
            "defined": int(defined.sum()),
            "total": int(defined.size),
            "nodata": float(_UNDEF),
            "crs": metadata.get("crs"),
            "units": metadata.get("z_units") or metadata.get("units"),
            "covered": int(covered.sum()),
            "uncovered": int((~covered).sum()),
            "negative_weight_cells": int(
                (attributes["negative_weights"] < 0).sum()),
        },
        "points": {
            "n": int(np.asarray(x).size),
            "used": int(stats["n"]),
            "outliers": int(flags.sum()),
        },
        "residuals": {
            "rmse": stats["rmse"],
            "bias": stats["bias"],
            "weighted_mse": stats["weighted_mse"],
            "chi2": stats["chi2"],
            "dof": int(stats["dof"]),
            "values": stats["residuals"].tolist(),
        },
        "outlier_flags": flags.tolist(),
        "metadata": metadata,
        "provenance": build_provenance(task, sources),
    }
