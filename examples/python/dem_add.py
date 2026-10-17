"""The weighted terrain example -- examples/globe/dem_add.tcl, written in Python.

    python3 examples/python/dem_add.py

The same SRTM tile as dem.py, but the DEM enters as a rule with a weight
instead of as a hard constraint: ``completer`` first, then ``dem_add``, so the
surface is a compromise between a smooth trend and the measured relief.  The
weight decides how closely the result follows the tile.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "globe")
TILE = "N00E006.hgt"


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_dem_add", tol=1e-5)

    assert all(task.dem_load_hgt_zip(os.path.join(DATA, TILE + ".zip"), TILE))

    task.grid(6.4, 6.8, 0.0005, 0, 0.48, 0.0005)

    task.completer()
    task.dem_add(1, TILE)

    task.solve()
    task.grid_unload()
    return task


def main():
    task = build()
    task.save("dem_add.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved dem_add.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.1f max=%.1f mean=%.1f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
