"""Out-of-core point gridding on a tiled grid.

The engine still solves one regular grid at a time, but the result does not
have to fit in RAM: each tile is written into a ``numpy.memmap``.  Tiles
overlap by ``halo`` nodes, and only the inner part is copied, so the solve near
a tile edge sees the same data as the solve in the middle.

This is a point-only driver.  It deliberately does not guess how to clip
contours, areas or surfaces; use a full task when those rules are needed.
"""

import os
import tempfile

import numpy as np

from surfit import UNDEF_VALUE, Session


def _write_points(path, x, y, z):
    with open(path, "w", encoding="ascii") as stream:
        for xi, yi, zi in zip(x, y, z):
            stream.write("%.17g\t%.17g\t%.17g\n" % (xi, yi, zi))


def _grid_size(start, end, step):
    return int(round((end - start) / step)) + 1


def solve_point_tiles(x, y, z, extent, step, inner=256, halo=32,
                      weights=None, completer=(1, 1.6), tol=1e-6,
                      map_name="tiled", memmap_path="tiled.f64",
                      crs=None, geotiff_path=None, progress=None):
    """Solve a point task tile by tile into a memmap.

    ``extent`` is ``(xmin, xmax, ymin, ymax)``.  ``inner`` and ``halo`` are in
    grid nodes.  ``completer`` is the pair passed to ``Session.completer``;
    pass ``None`` for points only.  ``progress(tx, ty, points)`` is optional.

    Returns ``{"values": memmap, "path": ..., "extent": dict, "tiles": n}``.
    The memmap is the caller's to keep or close; it remains open.
    """
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
    xmin, xmax, ymin, ymax = (float(value) for value in extent)
    if step <= 0:
        raise ValueError("step must be positive")
    if inner < 1 or halo < 0:
        raise ValueError("inner must be positive and halo non-negative")

    nx = _grid_size(xmin, xmax, step)
    ny = _grid_size(ymin, ymax, step)
    parent = os.path.dirname(os.path.abspath(memmap_path))
    os.makedirs(parent, exist_ok=True)
    if os.path.exists(memmap_path):
        os.remove(memmap_path)
    values = np.memmap(memmap_path, dtype="float64", mode="w+",
                       shape=(ny, nx))
    values[:] = UNDEF_VALUE
    values.flush()

    tiles = 0
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        for j0 in range(0, ny, inner):
            j1 = min(ny, j0 + inner)
            for i0 in range(0, nx, inner):
                i1 = min(nx, i0 + inner)
                gj0 = max(0, j0 - halo)
                gj1 = min(ny, j1 + halo)
                gi0 = max(0, i0 - halo)
                gi1 = min(nx, i1 + halo)
                tx0 = xmin + gi0 * step
                tx1 = xmin + (gi1 - 1) * step
                ty0 = ymin + gj0 * step
                ty1 = ymin + (gj1 - 1) * step
                selected = ((x >= tx0 - step / 2.0) &
                            (x <= tx1 + step / 2.0) &
                            (y >= ty0 - step / 2.0) &
                            (y <= ty1 + step / 2.0))
                count = int(selected.sum())
                if count == 0:
                    continue
                _write_points(path, x[selected], y[selected], z[selected])
                task = Session(map_name=map_name, tol=tol)
                assert all(task.read_points(path, "p",
                                            weights=weights[selected]))
                task.grid(tx0, tx1, step, ty0, ty1, step)
                task.points("p")
                if completer is not None:
                    task.completer(*completer)
                task.solve()
                tile_values = task.values()
                expected = (gj1 - gj0, gi1 - gi0)
                if tile_values.shape != expected:
                    raise RuntimeError(
                        "tile %d,%d returned %s, expected %s"
                        % (i0, j0, tile_values.shape, expected))
                values[j0:j1, i0:i1] = tile_values[
                    j0 - gj0:j1 - gj0, i0 - gi0:i1 - gi0]
                values.flush()
                tiles += 1
                if progress is not None:
                    progress(i0, j0, count)

    extent_dict = {
        "count_x": nx, "count_y": ny,
        "min_x": xmin, "max_x": xmax,
        "min_y": ymin, "max_y": ymax,
        "step_x": step, "step_y": step,
    }
    if geotiff_path is not None:
        from surfit.geotiff import save_geotiff
        save_geotiff(geotiff_path, values, extent_dict, crs)
    return {"values": values, "path": memmap_path,
            "extent": extent_dict, "tiles": tiles}
