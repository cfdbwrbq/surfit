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


def _bounds_2d(x, y, bounds):
    if bounds is None:
        xmin, xmax = float(np.min(x)), float(np.max(x))
        ymin, ymax = float(np.min(y)), float(np.max(y))
    elif hasattr(bounds, "get"):
        xmin = float(bounds["min_x"])
        xmax = float(bounds["max_x"])
        ymin = float(bounds["min_y"])
        ymax = float(bounds["max_y"])
    else:
        xmin, xmax, ymin, ymax = (float(value) for value in bounds)
    if not (xmin < xmax and ymin < ymax):
        raise ValueError("bounds must have min_x < max_x and min_y < max_y")
    if (np.any(x < xmin) or np.any(x > xmax)
            or np.any(y < ymin) or np.any(y > ymax)):
        raise ValueError("all points must lie inside bounds")
    return xmin, xmax, ymin, ymax


def _clip(polygon, a, b, c):
    """Clip a convex polygon to ``a*x + b*y <= c`` (Sutherland-Hodgman)."""
    output = []
    eps = 1e-12
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        first_value = a * first[0] + b * first[1] - c
        second_value = a * second[0] + b * second[1] - c
        if first_value <= eps:
            output.append(first)
        if (first_value > eps and second_value < -eps) or (
                first_value < -eps and second_value > eps):
            fraction = first_value / (first_value - second_value)
            output.append((first[0] + fraction * (second[0] - first[0]),
                           first[1] + fraction * (second[1] - first[1])))
    return output


def _area(polygon):
    if len(polygon) < 3:
        return 0.0
    total = 0.0
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        total += first[0] * second[1] - second[0] * first[1]
    return abs(total) / 2.0


def _clip_rectangle(polygon, bounds):
    xmin, xmax, ymin, ymax = bounds
    for a, b, c in ((-1.0, 0.0, -xmin), (1.0, 0.0, xmax),
                    (0.0, -1.0, -ymin), (0.0, 1.0, ymax)):
        polygon = _clip(polygon, a, b, c)
        if not polygon:
            return []
    return polygon


def _cell_area(point, others, bounds):
    polygon = _clip_rectangle(
        [(bounds[0], bounds[2]), (bounds[1], bounds[2]),
         (bounds[1], bounds[3]), (bounds[0], bounds[3])], bounds)
    for index in range(others.shape[0]):
        other = others[index]
        a = 2.0 * (other[0] - point[0])
        b = 2.0 * (other[1] - point[1])
        c = (other[0] ** 2 + other[1] ** 2
             - point[0] ** 2 - point[1] ** 2)
        polygon = _clip(polygon, a, b, c)
        if not polygon:
            return 0.0
    return _area(polygon)


def voronoi_weights(x, y, bounds=None):
    """Polygonal declustering weights for 2D sample locations.

    The weight is proportional to the inverse area of the point's Voronoi cell
    clipped to ``bounds``.  ``bounds`` is a mapping with
    ``min_x/max_x/min_y/max_y`` or ``(xmin, xmax, ymin, ymax)``; the default is
    the point bounding box.  The result has mean 1, so it can be written with
    ``pnts_set_weights``; zero-area duplicates are split between the duplicate
    points.

    This is 2D on purpose: in a surfit surface ``z`` is the measured value,
    not a spatial coordinate.  Use a separate 3D helper only for true 3D
    samples.  SciPy is optional; it supplies the Voronoi topology, while the
    clipping is done here.
    """
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if x.size != y.size:
        raise ValueError("x and y must have the same length")
    if x.size < 3:
        raise ValueError("voronoi_weights needs at least three points")
    try:
        from scipy.spatial import Voronoi, QhullError
    except ImportError as error:
        raise ImportError(
            "voronoi_weights needs scipy; install the scipy package"
        ) from error
    xmin, xmax, ymin, ymax = _bounds_2d(x, y, bounds)
    unique, inverse, counts = np.unique(
        np.column_stack((x, y)), axis=0, return_inverse=True,
        return_counts=True)
    if unique.shape[0] < 3:
        raise ValueError("only %d distinct points" % unique.shape[0])
    if np.linalg.matrix_rank(unique - unique[0]) < 2:
        raise ValueError("points are collinear; 2D Voronoi area is undefined")
    try:
        diagram = Voronoi(unique)
    except QhullError as error:
        raise ValueError("scipy could not build the Voronoi diagram") from error
    bounds_tuple = (xmin, xmax, ymin, ymax)
    areas = np.zeros(unique.shape[0], dtype=float)
    for index in range(unique.shape[0]):
        region = diagram.regions[diagram.point_region[index]]
        if region and -1 not in region:
            polygon = [diagram.vertices[vertex] for vertex in region]
            areas[index] = _area(_clip_rectangle(polygon, bounds_tuple))
        else:
            others = np.delete(unique, index, axis=0)
            areas[index] = _cell_area(unique[index], others, bounds_tuple)
    if np.any(areas <= 0):
        raise ValueError("a Voronoi cell has zero area; check duplicates/bounds")
    raw = (1.0 / areas)[inverse] / counts[inverse]
    if not np.isfinite(raw).all() or raw.sum() <= 0:
        raise ValueError("could not build finite non-negative weights")
    return raw / raw.mean()
