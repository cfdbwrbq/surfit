"""Cross-sections through a SurfaceStack.

The output is plain arrays: distance along the polyline, sampled coordinates,
one profile per layer and optional calibrated-interval profiles.  It is a
sampling utility, not a second interpolation grid.
"""

import numpy as np

_UNDEF = float(np.finfo(np.float32).max)


def _path_samples(path_x, path_y, samples):
    path_x = np.asarray(path_x, dtype=float).ravel()
    path_y = np.asarray(path_y, dtype=float).ravel()
    if path_x.size != path_y.size:
        raise ValueError("path_x and path_y must have the same length")
    if path_x.size < 2:
        raise ValueError("a section needs at least two path nodes")
    segment = np.hypot(np.diff(path_x), np.diff(path_y))
    cumulative = np.concatenate(([0.0], np.cumsum(segment)))
    total = cumulative[-1]
    if total <= 0:
        raise ValueError("the section path has zero length")
    count = int(samples) if samples is not None else 200
    if count < 2:
        raise ValueError("samples must be at least two")
    distance = np.linspace(0.0, total, count)
    x = np.interp(distance, cumulative, path_x)
    y = np.interp(distance, cumulative, path_y)
    return distance, x, y


def _sample(values, extent, x, y, method):
    values = np.asarray(values, dtype=float)
    x0 = float(extent["min_x"])
    y0 = float(extent["min_y"])
    sx = float(extent["step_x"])
    sy = float(extent["step_y"])
    nx = int(extent["count_x"])
    ny = int(extent["count_y"])
    fx = (x - x0) / sx
    fy = (y - y0) / sy
    if method == "nearest":
        ix = np.rint(fx).astype(int)
        iy = np.rint(fy).astype(int)
        outside = (ix < 0) | (ix >= nx) | (iy < 0) | (iy >= ny)
        ix = np.clip(ix, 0, nx - 1)
        iy = np.clip(iy, 0, ny - 1)
        result = values[iy, ix].copy()
        result[outside] = np.nan
    elif method == "bilinear":
        xmax = x0 + (nx - 1) * sx
        ymax = y0 + (ny - 1) * sy
        outside = ((x < x0) | (x > xmax) | (y < y0) | (y > ymax))
        fx = np.clip(fx, 0.0, nx - 1.0)
        fy = np.clip(fy, 0.0, ny - 1.0)
        ix = np.floor(fx).astype(int)
        iy = np.floor(fy).astype(int)
        tx = fx - ix
        ty = fy - iy
        ix = np.clip(ix, 0, nx - 2)
        iy = np.clip(iy, 0, ny - 2)
        tx[fx >= nx - 1] = 1.0
        ty[fy >= ny - 1] = 1.0
        v00 = values[iy, ix]
        v10 = values[iy, ix + 1]
        v01 = values[iy + 1, ix]
        v11 = values[iy + 1, ix + 1]
        result = (v00 * (1 - tx) * (1 - ty) + v10 * tx * (1 - ty) +
                  v01 * (1 - tx) * ty + v11 * tx * ty)
        result[outside] = np.nan
    else:
        raise ValueError("method must be 'nearest' or 'bilinear'")
    result[np.abs(result) >= _UNDEF * 0.9] = np.nan
    result[~np.isfinite(result)] = np.nan
    return result


def stack_section(stack, path_x, path_y, samples=200, method="bilinear"):
    """Sample every layer (and its interval) along a polyline."""
    extent = stack.extent()
    distance, x, y = _path_samples(path_x, path_y, samples)
    layers = {}
    intervals = {}
    for name in stack.layer_names():
        layers[name] = _sample(stack.values(name), extent, x, y, method)
        try:
            interval = stack.interval(name)
        except KeyError:
            continue
        intervals[name] = {
            "lower": _sample(interval["lower"], extent, x, y, method),
            "upper": _sample(interval["upper"], extent, x, y, method),
        }
    return {
        "distance": distance,
        "x": x,
        "y": y,
        "layers": layers,
        "intervals": intervals,
        "extent": extent,
        "samples": int(distance.size),
        "method": method,
    }
