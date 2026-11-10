"""Optional coordinate reference system helpers.

surfit's engine works in Cartesian grid coordinates.  This module does not
pretend that a regular grid is invariant under reprojection: it transforms
points and reports the bounds of a transformed extent, and the caller decides
whether to rebuild the grid.  ``pyproj`` is optional; importing this module is
safe without it, and every function raises a clear ImportError when called.
"""

import numpy as np


def _pyproj():
    try:
        import pyproj
    except ImportError as error:
        raise ImportError(
            "reprojection needs pyproj; install the pyproj package"
        ) from error
    return pyproj


def is_geographic_crs(crs):
    """Whether ``crs`` is a geographic (degree) coordinate system."""
    return bool(_pyproj().CRS.from_user_input(crs).is_geographic)


def require_projected(crs):
    """Raise when ``crs`` is geographic; anisotropy in degrees is a trap."""
    if is_geographic_crs(crs):
        raise ValueError(
            "%r is geographic; reproject to a projected CRS before gridding"
            % (crs,))
    return crs


def to_crs(x, y, source, target):
    """Transform arrays of points from ``source`` to ``target`` with pyproj."""
    pyproj = _pyproj()
    transformer = pyproj.Transformer.from_crs(
        source, target, always_xy=True)
    return transformer.transform(x, y)


def transform_extent(extent, source, target, samples=32):
    """Bounds of a transformed extent without claiming a new regular grid.

    The four edges are sampled so a curved projected boundary is not reduced
    to two corners.  Returns only ``min_x/max_x/min_y/max_y``; a caller that
    wants a grid must rebuild it at the target resolution.
    """
    x_min = float(extent["min_x"])
    x_max = float(extent["max_x"])
    y_min = float(extent["min_y"])
    y_max = float(extent["max_y"])
    samples = max(int(samples), 2)
    xs = np.linspace(x_min, x_max, samples)
    ys = np.linspace(y_min, y_max, samples)
    edge_x = np.concatenate((xs, xs, np.full(samples, x_min),
                             np.full(samples, x_max)))
    edge_y = np.concatenate((np.full(samples, y_min),
                             np.full(samples, y_max), ys, ys))
    target_x, target_y = to_crs(edge_x, edge_y, source, target)
    return {
        "min_x": float(np.min(target_x)),
        "max_x": float(np.max(target_x)),
        "min_y": float(np.min(target_y)),
        "max_y": float(np.max(target_y)),
    }
