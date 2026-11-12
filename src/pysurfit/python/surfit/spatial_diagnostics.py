"""Spatial diagnostics for residuals: autocorrelation, variogram and error by
distance or group.

These helpers do not solve anything.  They make structured residuals visible
after a solve, complementing the global RMSE and cross-validation report.
"""

import math

import numpy as np


def morans_i(values, mask=None, neighbors=4):
    """Moran's I of a regular grid with rook (4-neighbour) weights.

    ``values`` is a (count_y, count_x) array; non-finite cells are skipped.
    ``mask`` optionally marks the cells to include.  Returns ``i``, expected
    value, variance, z-score, two-sided p-value and graph counts.
    """
    if neighbors != 4:
        raise ValueError("only rook (4-neighbour) weights are supported")
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError("values must be a 2D grid")
    valid = np.isfinite(values)
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != values.shape:
            raise ValueError("mask shape must match values")
        valid &= mask
    count = int(valid.sum())
    if count < 3:
        raise ValueError("Moran's I needs at least three valid cells")
    index = -np.ones(values.shape, dtype=np.int64)
    index[valid] = np.arange(count)
    source = []
    target = []
    for dy, dx in ((1, 0), (0, 1)):
        left = index[:values.shape[0] - dy,
                     :values.shape[1] - dx]
        right = index[dy:, dx:]
        keep = (left >= 0) & (right >= 0)
        source.append(left[keep])
        target.append(right[keep])
    source = np.concatenate(source)
    target = np.concatenate(target)
    weights_total = 2.0 * source.size
    z = values[valid] - values[valid].mean()
    numerator = float(np.sum(z[source] * z[target]) * 2.0)
    denominator = float(np.sum(z * z))
    if denominator == 0:
        raise ValueError("Moran's I is undefined for a constant field")
    moran = (count / weights_total) * (numerator / denominator)
    expected = -1.0 / (count - 1.0)
    degree = 2.0 * source.size
    s1 = 2.0 * source.size
    s2 = float(2.0 * source.size)
    variance = ((count * count * s1 - count * s2 + 3.0 * weights_total ** 2)
                / ((count * count - 1.0) * weights_total ** 2)
                - expected * expected)
    if variance <= 0:
        raise ValueError("Moran's I variance is not positive")
    z_score = (moran - expected) / math.sqrt(variance)
    p_value = math.erfc(abs(z_score) / math.sqrt(2.0))
    return {
        "i": float(moran),
        "expected": float(expected),
        "variance": float(variance),
        "z": float(z_score),
        "p": float(p_value),
        "n": count,
        "pairs": int(source.size),
        "neighbors": 4,
        "weights_total": float(weights_total),
        "degree": float(degree),
    }


def residual_variogram(x, y, residuals, bins=20, max_lag=None,
                       estimator="classical"):
    """Experimental semivariogram of residuals at point locations."""
    from surfit.variogram import experimental_variogram

    return experimental_variogram(
        x, y, residuals, bins=bins, max_lag=max_lag, estimator=estimator)


def distance_to_data(x, y, data_x, data_y, chunk=4096):
    """Euclidean distance from each location to its nearest data point."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    data_x = np.asarray(data_x, dtype=float).ravel()
    data_y = np.asarray(data_y, dtype=float).ravel()
    if x.size != y.size:
        raise ValueError("x and y must have the same length")
    if data_x.size != data_y.size:
        raise ValueError("data_x and data_y must have the same length")
    if data_x.size == 0:
        raise ValueError("at least one data point is required")
    result = np.empty(x.size, dtype=float)
    for start in range(0, x.size, chunk):
        stop = min(start + chunk, x.size)
        dx = x[start:stop, None] - data_x[None, :]
        dy = y[start:stop, None] - data_y[None, :]
        result[start:stop] = np.min(np.hypot(dx, dy), axis=1)
    return result


def error_by_distance(distance, residuals, bins=10, max_distance=None):
    """Bin residuals by distance to data and report error statistics."""
    distance = np.asarray(distance, dtype=float).ravel()
    residuals = np.asarray(residuals, dtype=float).ravel()
    if distance.size != residuals.size:
        raise ValueError("distance and residuals must have the same length")
    keep = np.isfinite(distance) & np.isfinite(residuals)
    distance = distance[keep]
    residuals = residuals[keep]
    if distance.size == 0:
        raise ValueError("no finite distance/residual pairs")
    upper = float(max_distance) if max_distance is not None else float(
        distance.max())
    if upper <= 0:
        raise ValueError("max_distance must be positive")
    edges = np.linspace(0.0, upper, int(bins) + 1)
    index = np.clip(np.digitize(distance, edges) - 1, 0, int(bins) - 1)
    rows = []
    for number in range(int(bins)):
        selected = residuals[index == number]
        rows.append({
            "distance": float((edges[number] + edges[number + 1]) / 2.0),
            "count": int(selected.size),
            "bias": (float(np.mean(selected)) if selected.size else None),
            "mae": (float(np.mean(np.abs(selected))) if selected.size else None),
            "rmse": (float(np.sqrt(np.mean(selected ** 2)))
                     if selected.size else None),
        })
    return rows


def error_by_group(residuals, groups):
    """Residual bias/MAE/RMSE per group, preserving sorted group order."""
    residuals = np.asarray(residuals, dtype=float).ravel()
    groups = np.asarray(groups).ravel()
    if residuals.size != groups.size:
        raise ValueError("groups must have one value per residual")
    rows = []
    for group in np.unique(groups):
        selected = residuals[groups == group]
        selected = selected[np.isfinite(selected)]
        rows.append({
            "group": group.item() if hasattr(group, "item") else group,
            "count": int(selected.size),
            "bias": float(np.mean(selected)) if selected.size else None,
            "mae": float(np.mean(np.abs(selected))) if selected.size else None,
            "rmse": (float(np.sqrt(np.mean(selected ** 2)))
                     if selected.size else None),
        })
    return rows
