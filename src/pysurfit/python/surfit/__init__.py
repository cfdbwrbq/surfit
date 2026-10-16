"""Python interface to the surfit gridding engine.

surfit computes a regular grid from scattered data (points, curves, contours,
surfaces, areas) under "gridding rules": functionals, inequalities, trends,
faults and weights.  This package drives the original C++ engine, so results
are identical to those of the Tcl front end -- see
``src/pysurfit/tests/test_parity.py`` and ``run_tcl_suite.py``.

The high-level entry point is :class:`Session`::

    import surfit

    task = surfit.Session(map_name="map_area", tol=5.01187e-06)
    task.read_areas("data/area1.txt", "area1")
    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(10, "area1")
    task.completer(1, 1.6)
    task.solve()
    grid = task.values()              # numpy array, (count_y, count_x)

Every command the compiled core exposes is re-exported here under the same
name the Tcl front end uses, so a Tcl script maps one call to one call.
"""

import fnmatch

import numpy as np

from . import _surfit as _core

#: Undefined grid nodes carry FLT_MAX, the core's `undef_value`.
UNDEF_VALUE = float(np.finfo(np.float32).max)


def defined_mask(values_array):
    """Boolean mask that is True where `values_array` holds a defined number."""
    return ~np.isclose(values_array, UNDEF_VALUE, rtol=1e-6)


def surf_names():
    """Names of all surfaces currently in memory."""
    return [_core.surf_name_at(pos) for pos in range(_core.surf_count())]


def surf_index(pattern="*"):
    """Index of the first surface matching a shell-style pattern, or -1.

    The Tcl front end selects objects the same way, by name with wildcards.
    """
    for pos, name in enumerate(surf_names()):
        if fnmatch.fnmatchcase(name, pattern):
            return pos
    return -1


def values(pattern="*"):
    """Values of the first surface matching `pattern`, as a numpy array."""
    pos = surf_index(pattern)
    if pos < 0:
        raise KeyError("no surface matches %r" % (pattern,))
    return _core.surf_values(pos)


class Session:
    """One gridding task.

    The core keeps its data in process-wide globals, so a Session resets that
    state when it is created and drives it through the command functions.  Two
    Sessions cannot be used at the same time yet: that needs the per-instance
    context planned for stage L2.
    """

    def __init__(self, map_name="map", tol=None):
        clear_data()
        set_map_name(map_name)
        if tol is not None:
            set_tol(tol)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        clear_data()
        return False

    def read_areas(self, path, name):
        """Loads polygon areas from a text file under the given name."""
        return area_read(path, name)

    def grid(self, start_x, end_x, step_x, start_y, end_y, step_y, name=None):
        """Creates the target grid; all rules are defined on it."""
        return grid_get(start_x, end_x, step_x, start_y, end_y, step_y, name)

    def area(self, value, name="*"):
        """Rule: the surface equals `value` inside the area.

        `value` may be the string "undef" to leave the area undefined.
        """
        return area(value, name)

    def area_add(self, value, weight, name="*"):
        """Like :meth:`area`, but with a weight, added to the previous rule."""
        return area_add(value, weight, name)

    def completer(self, d1=1, d2=2, alpha=0, w=1):
        """Rule: the surface should tend to be constant or a plane."""
        return completer(d1, d2, alpha, w)

    def add_surface(self, values_array, start_x, step_x, start_y, step_y,
                    name):
        """Registers a (count_y, count_x) float64 array as a named surface."""
        return add_surface(values_array, start_x, step_x, start_y, step_y,
                           name)

    def solve(self):
        """Runs the gridding algorithm."""
        surfit()

    def save(self, path, name="*"):
        """Saves a surface to a surfit data file."""
        return surf_save(path, name)

    def names(self):
        """Names of the surfaces in memory."""
        return surf_names()

    def values(self, pattern="*"):
        """Values of the first surface matching `pattern`, as a numpy array."""
        return values(pattern)


def _reexport_commands():
    """Makes every compiled command available under its Tcl name.

    Names already defined above win, so the richer Python helpers stay in
    place while the plain command wrappers are re-exported wholesale.
    """
    taken = set(globals())
    for name in dir(_core):
        if name.startswith("_") or name in taken:
            continue
        globals()[name] = getattr(_core, name)


_reexport_commands()
del _reexport_commands

__all__ = sorted(name for name in globals() if not name.startswith("_"))
