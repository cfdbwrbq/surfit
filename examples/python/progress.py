"""Shows solver progress with tqdm.

    python3 examples/python/progress.py

The engine reports each solve and every iteration through its logging; the
progress() context manager turns that into a bar.  tqdm is optional, so this
prints a note instead of failing when it is missing.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area5")


def main():
    task = surfit.Session(map_name="map_area", tol=5.01187e-006)

    for name in AREAS:
        task.read_areas(os.path.join(DATA, "%s.txt" % name), name)

    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")

    try:
        import tqdm  # noqa: F401
    except ImportError:
        print("tqdm is not installed; running without a progress bar")
        task.solve()
    else:
        # The bar lives on stderr, next to the engine's own console output.
        with surfit.progress():
            task.solve()

    grid = task.values()
    print("solved %s, %d of %d nodes defined"
          % (grid.shape, surfit.defined_mask(grid).sum(), grid.size))


if __name__ == "__main__":
    main()
