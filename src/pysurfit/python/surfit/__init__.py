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
import re
import sys
import time

import numpy as np

from . import _surfit as _core
from ._viewer import render_html, save_viewer, viewer

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


def values(pattern=None):
    """Values of a surface, as a (count_y, count_x) float64 array.

    Without a pattern this is the most recently created surface, which is the
    result of the last solve.  A trend or any other surface added along the way
    would otherwise be picked up instead, since it comes first in the list.
    With a pattern the first matching surface is used.
    """
    if pattern is None:
        pos = _core.surf_count() - 1
        if pos < 0:
            raise KeyError("no surfaces in memory")
        return _core.surf_values(pos)
    pos = surf_index(pattern)
    if pos < 0:
        raise KeyError("no surface matches %r" % (pattern,))
    return _core.surf_values(pos)


class _ProgressBase:
    """Parses the engine's log messages into progress events.

    The solver announces each run as ``<name>: (<cells>) .......`` and then
    reports every iteration as `` iter : <n>, error : <e>, <t> sec``, while the
    outer loop announces ``* Phase <n>, grid size = <w> x <h>``.
    """

    _PHASE = re.compile(r"Phase (\d+), grid size = (\d+) x (\d+)")
    _SOLVER = re.compile(r"^([A-Za-z0-9_]+): \((\d+)\)")
    _ITERATION = re.compile(r"iter\s*:\s*(\d+).*?error\s*:\s*([0-9eE.+-]+)")

    def __enter__(self):
        self._open()
        _core.set_log_handler(self._observe)
        return self

    def __exit__(self, *exc_info):
        _core.clear_log_handler()
        self._close()
        return False

    def _open(self):
        pass

    def _close(self):
        pass

    def on_phase(self, number, width, height):
        """The outer loop moved to a finer grid."""

    def on_solve(self, solver, cells):
        """A new linear system is being solved."""

    def on_iteration(self, step, error):
        """The solver finished another iteration."""

    def on_message(self, text):
        """Any other message from the engine."""

    def _observe(self, level, message):
        text = message.strip()
        if not text:
            return
        phase = self._PHASE.search(text)
        if phase:
            self.on_phase(*phase.groups())
            return
        solver = self._SOLVER.match(text)
        if solver:
            self.on_solve(*solver.groups())
            return
        iteration = self._ITERATION.search(text)
        if iteration:
            self.on_iteration(int(iteration.group(1)), iteration.group(2))
            return
        self.on_message(text)


class _BarProgress(_ProgressBase):
    """Draws the events as a tqdm bar on stderr."""

    def __init__(self, disable=False, **tqdm_kwargs):
        self._disable = disable
        self._tqdm_kwargs = tqdm_kwargs
        self._bar = None

    def _open(self):
        try:
            from tqdm import tqdm
        except ImportError:
            raise ImportError(
                "progress(style='bar') needs tqdm; install it with "
                "`pip install surfit[progress]` or `pip install tqdm`")
        self._bar = tqdm(unit="iter", desc="gridding", disable=self._disable,
                         dynamic_ncols=True, **self._tqdm_kwargs)

    def _close(self):
        if self._bar is not None:
            self._bar.close()
            self._bar = None

    def _set_description(self, text):
        """tqdm's set_description() appends ": " on top of the one the bar
        format already adds; set_description_str() does not."""
        setter = getattr(self._bar, "set_description_str", None)
        if setter is not None:
            setter(text)
        else:
            self._bar.set_description(text)

    def on_phase(self, number, width, height):
        if self._bar is not None:
            self._set_description("phase %s %sx%s" % (number, width, height))

    def on_solve(self, solver, cells):
        if self._bar is not None:
            self._bar.reset()
            self._set_description("%s (%s cells)" % (solver, cells))

    def on_iteration(self, step, error):
        if self._bar is None:
            return
        if step > self._bar.n:
            self._bar.update(step - self._bar.n)
        self._bar.set_postfix_str("err %s" % error)


class _LineProgress(_ProgressBase):
    """Writes one line per event, for logs, CI and captured output.

    A terminal bar animates with carriage returns, so anywhere the output is
    captured rather than displayed -- a CI log, a notebook cell, an agent
    transcript -- the frames overwrite each other and only the last survives.
    One line per event survives intact.
    """

    def __init__(self, every=2.0, stream=None):
        self._every = every
        self._stream = stream if stream is not None else sys.stderr
        self._last = 0.0
        self._description = "gridding"

    def _write(self, text):
        print(text, file=self._stream, flush=True)

    def on_phase(self, number, width, height):
        self._description = "phase %s %sx%s" % (number, width, height)

    def on_solve(self, solver, cells):
        self._last = 0.0
        self._description = "%s (%s cells)" % (solver, cells)
        self._write("-- %s" % self._description)

    def on_iteration(self, step, error):
        now = time.monotonic()
        if step > 1 and now - self._last < self._every:
            return
        self._last = now
        self._write("   %s: iter %d, err %s"
                    % (self._description, step, error))


def progress(disable=False, style=None, **tqdm_kwargs):
    """Context manager reporting the solver's progress.

    ::

        with surfit.progress():
            task.solve()

    ``style`` selects how it is rendered:

    ``"bar"``
        a tqdm bar; needs tqdm (``pip install surfit[progress]``).
    ``"lines"``
        one line per event, throttled by ``every`` seconds.  Use this in CI
        logs, notebooks, and anywhere the output is captured rather than shown
        live on a terminal.
    ``None``
        a bar when stderr is a terminal, lines otherwise.

    The mechanism is the ordinary log hook, so ``set_log_handler`` can be used
    directly when you want the messages yourself.
    """
    if style is None:
        style = "bar" if sys.stderr.isatty() else "lines"
    if style == "bar":
        return _BarProgress(disable=disable, **tqdm_kwargs)
    if style == "lines":
        return _LineProgress(**tqdm_kwargs)
    raise ValueError("style must be 'bar', 'lines' or None, not %r" % (style,))


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

    def read_points(self, path, name, **columns):
        """Loads scattered points from a columned text file.

        Extra keyword arguments are passed on to :func:`pnts_read`, so
        ``columns=...`` maps to col1..col4, delimiter, skip_lines.
        """
        return pnts_read(path, name, **columns)

    def read_curves(self, path, name):
        """Loads 2D curves from a columned text file."""
        return curv_read(path, name)

    def read_contours(self, path, name):
        """Loads 3D contours from a columned text file."""
        return cntr_read(path, name)

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

    def __getattr__(self, name):
        """Delegates any core command, so ``task.points(...)`` works like
        ``points(...)``.

        Every command is reachable without listing it here, and the Session
        stays in step with the bindings as they grow.
        """
        if not name.startswith("_") and name in _COMMANDS:
            return globals()[name]
        raise AttributeError("%r object has no attribute %r"
                             % (type(self).__name__, name))

    def names(self):
        """Names of the surfaces in memory."""
        return surf_names()

    def surf_index(self, pattern="*"):
        """Index of the first surface matching `pattern`, or -1."""
        return surf_index(pattern)

    def values(self, pattern=None):
        """Values of a surface; without a pattern, the most recent one."""
        return values(pattern)

    def viewer(self, **kwargs):
        """Self-contained HTML page for the result surface."""
        return viewer(**kwargs)

    def save_viewer(self, path, **kwargs):
        """Writes that page to ``path``."""
        return save_viewer(path, **kwargs)


#: Names re-exported from the compiled module, used by Session.__getattr__.
_COMMANDS = frozenset()


def _reexport_commands():
    """Makes every compiled command available under its Tcl name.

    Names already defined above win, so the richer Python helpers stay in
    place while the plain command wrappers are re-exported wholesale.
    """
    global _COMMANDS
    taken = set(globals())
    exported = []
    for name in dir(_core):
        if name.startswith("_") or name in taken:
            continue
        globals()[name] = getattr(_core, name)
        exported.append(name)
    _COMMANDS = frozenset(exported)


_reexport_commands()
del _reexport_commands

__all__ = sorted(name for name in globals() if not name.startswith("_"))
