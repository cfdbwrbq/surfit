"""Decluster dense sampling before a solve.

Points that share a cell are already averaged by the engine, but a dense line
or a cluster still dominates a global fit.  This helper reduces each
rectangular block to one representative and keeps the original points
available for residual diagnostics.  It is a preprocessing step, not a rule:
the caller decides whether the reduced set is appropriate.
"""

import numpy as np

_METHODS = ("mean", "nearest", "idw", "min", "max")


def _points(x, y, z, weights):
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
    return x, y, z, weights


def _block(block):
    if block is None:
        raise ValueError("decluster_points needs a block size")
    if np.isscalar(block):
        size = float(block)
        return size, size
    values = tuple(float(value) for value in block)
    if len(values) != 2 or min(values) <= 0:
        raise ValueError("block must be a positive number or an (x, y) pair")
    return values


def _representative(indices, x, y, z, weights, center, method):
    wx = weights[indices]
    total = float(wx.sum())
    if total <= 0:
        return None
    if method == "nearest":
        distance = np.hypot(x[indices] - center[0], y[indices] - center[1])
        chosen = indices[int(np.argmin(distance))]
        return x[chosen], y[chosen], z[chosen], weights[chosen]
    if method in ("min", "max"):
        chosen = indices[int(np.argmin(z[indices]) if method == "min"
                             else np.argmax(z[indices]))]
        return x[chosen], y[chosen], z[chosen], weights[chosen]
    if method == "mean":
        return (float(np.sum(wx * x[indices]) / total),
                float(np.sum(wx * y[indices]) / total),
                float(np.sum(wx * z[indices]) / total), total)
    distance = np.hypot(x[indices] - center[0], y[indices] - center[1])
    inverse = 1.0 / (distance * distance + np.finfo(float).eps)
    weight = wx * inverse
    weight_sum = float(weight.sum())
    return (float(np.sum(weight * x[indices]) / weight_sum),
            float(np.sum(weight * y[indices]) / weight_sum),
            float(np.sum(weight * z[indices]) / weight_sum), total)


def decluster_points(x, y, z, weights=None, method="mean", block=None):
    """Reduce each block to one representative point.

    ``method`` is ``"mean"`` (weighted centroid), ``"nearest"`` (closest to the
    block centre), ``"idw"`` (inverse-distance centroid), ``"min"`` or
    ``"max"`` (the point with the smallest/largest z).  The returned weights
    preserve the total mass for mean/IDW and the chosen point's weight
    otherwise.  Blocks with zero total weight are dropped.
    """
    if method not in _METHODS:
        raise ValueError("method must be one of %s" % ", ".join(_METHODS))
    x, y, z, weights = _points(x, y, z, weights)
    block_x, block_y = _block(block)
    col = np.floor((x - float(np.min(x))) / block_x).astype(int)
    row = np.floor((y - float(np.min(y))) / block_y).astype(int)
    index = row * (int(col.max()) + 1) + col
    groups = np.unique(index)
    reps = []
    for group in groups:
        members = np.flatnonzero(index == group)
        centre = (float(np.mean(x[members])), float(np.mean(y[members])))
        point = _representative(members, x, y, z, weights, centre, method)
        if point is not None:
            reps.append(point + (int(members.size),))
    if not reps:
        return {
            "x": np.array([]), "y": np.array([]), "z": np.array([]),
            "weights": np.array([]), "count": np.array([], dtype=int),
            "method": method, "block": block,
        }
    return {
        "x": np.array([row[0] for row in reps]),
        "y": np.array([row[1] for row in reps]),
        "z": np.array([row[2] for row in reps]),
        "weights": np.array([row[3] for row in reps]),
        "count": np.array([row[4] for row in reps], dtype=int),
        "method": method,
        "block": list(block) if isinstance(block, tuple) else block,
    }


# A short alias for callers that already use the "points_" command prefix.
decluster = decluster_points
