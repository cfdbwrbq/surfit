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

import contextlib
import fnmatch
import functools
import re
import sys
import threading
import time

import numpy as np

from surfit import _surfit as _core
from surfit._viewer import render_html, save_viewer, viewer

#: Undefined grid nodes carry FLT_MAX, the core's `undef_value`.
UNDEF_VALUE = float(np.finfo(np.float32).max)
_DEFAULT_RTOL = 1e-6
_ANY = "*"
_PRIVATE_PREFIX = "_"

#: Rules whose empty result normally means "the name matched nothing".
_STRICT_RULES = frozenset((
    "area_leq", "area_geq", "area_mean", "area_wmean",
    "area_surf_leq", "area_surf_geq", "points_leq", "points_geq",
    "contour_leq", "contour_geq", "curve_leq", "curve_geq",
    "mask_leq", "mask_geq", "mask_mean", "mask_wmean",
    "surface_leq", "surface_geq", "leq", "geq", "mean", "wmean",
))


def defined_mask(values_array):
    """Boolean mask that is True where `values_array` holds a defined number."""
    return ~np.isclose(values_array, UNDEF_VALUE, rtol=_DEFAULT_RTOL)


@contextlib.contextmanager
def serial_threads():
    """Temporarily force the current task's worker pool to one worker.

    The pool belongs to the installed task, so this only limits the task this
    thread is working on; other tasks in other threads keep their own pool.
    The previous size is restored on exit.
    """
    previous = get_threads()
    init_threads(1)
    try:
        yield
    finally:
        init_threads(previous)


def surf_names():
    """Names of all surfaces currently in memory."""
    return [_core.surf_name_at(pos) for pos in range(_core.surf_count())]


def surf_index(pattern=_ANY):
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

    _phase_re = re.compile(r"Phase (\d+), grid size = (\d+) x (\d+)")
    _solver_re = re.compile(r"^([A-Za-z0-9_]+): \((\d+)\)")
    _iteration_re = re.compile(r"iter\s*:\s*(\d+).*?error\s*:\s*([0-9eE.+-]+)")

    def __enter__(self):
        self._open()
        _core.set_log_handler(self._observe)
        return self

    def __exit__(self, *exc_info):
        _core.clear_log_handler()
        self._close()
        return False

    def _open(self):
        """Starts the display; subclasses must implement it."""
        raise NotImplementedError

    def _close(self):
        """Stops the display; subclasses must implement it."""
        raise NotImplementedError

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
        phase = self._phase_re.search(text)
        if phase:
            self.on_phase(*phase.groups())
            return
        solver = self._solver_re.match(text)
        if solver:
            self.on_solve(*solver.groups())
            return
        iteration = self._iteration_re.search(text)
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
        if setter:
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
        self._stream = stream or sys.stderr
        self._last = 0
        self._description = "gridding"

    def _write(self, text):
        print(text, file=self._stream, flush=True)

    def on_phase(self, number, width, height):
        self._description = "phase %s %sx%s" % (number, width, height)

    def on_solve(self, solver, cells):
        self._last = 0
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
    """One gridding task, with its own state.

    The engine keeps its working data in globals, so a Session owns a state and
    installs it before every call it makes.  Two Sessions can therefore be used
    in one process without one wiping the other::

        first = surfit.Session("first")
        second = surfit.Session("second")
        first.read_areas(...)    # each call switches to that task
        second.read_areas(...)

    The DEMs belong to the task as well: a Session starts with none of its own
    and gets a fresh container, so two tasks may load different rasters under
    the same name.  The module-level functions keep using the library's own
    container, which is where a DEM loaded outside a Session lives.

    The engine's globals are thread-local, so every call installs this task in
    the calling thread only.  Two Sessions in two threads therefore run at the
    same time instead of serializing, and each keeps its own data, settings,
    DEMs, logs and worker pool.  Calls on the same Session are still serialized
    by a per-session re-entrant lock, because the task's state is shared while
    one thread uses it.
    """

    def __init__(self, map_name="map", tol=None, metadata=None, strict=False,
                 serial=False):
        self._map_name = map_name
        self._metadata = dict(metadata or {})
        self._strict = bool(strict)
        self._serial = bool(serial)
        # One re-entrant lock per task: two calls on the same Session must not
        # use its state at the same time.  Calls on different Sessions do not
        # need to exclude each other any more -- the engine's globals are
        # thread-local.
        self._lock = threading.RLock()
        with self._lock:
            self._state = _core.state_create()
            self._globe = _core.globe_state_create()
            self._activate()
            set_map_name(map_name)
            if tol is not None:
                set_tol(tol)
            # Store the settings into the task now, so it can be installed in
            # another thread without losing them.
            _core.state_store()

    @property
    def metadata(self):
        """A copy of the task's provenance metadata."""
        return dict(self._metadata)

    def set_metadata(self, **values):
        """Adds CRS, units, source or other provenance fields."""
        self._metadata.update(values)
        return self.metadata

    def save_metadata(self, path):
        """Writes the metadata as JSON next to the saved surface."""
        import json

        from surfit.provenance import build_provenance

        document = dict(self._metadata)
        document["map_name"] = self._map_name
        document["provenance"] = build_provenance(self)
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return path

    def _activate(self):
        """Makes this task's state and DEM container the active ones."""
        state = getattr(self, "_state", 0)
        if state:
            _core.state_install(state)
        globe = getattr(self, "_globe", 0)
        if globe:
            _core.globe_state_install(globe)

    def _call(self, target, *args, **kwargs):
        with self._lock:
            self._activate()
            result = target(*args, **kwargs)
            _core.state_store()
        if (self._strict and getattr(target, "__name__", "") in _STRICT_RULES
                and not result):
            raise ValueError("%s matched no data" % target.__name__)
        return result

    def close(self):
        """Frees this task's state and everything it holds.

        The rules are freed before the DEMs: a DEM rule keeps a pointer to its
        DEM but does not own it, so the two orders do not crash, while freeing
        the DEMs first would leave the rules pointing at freed rasters.
        """
        lock = getattr(self, "_lock", None)
        if lock is None:
            return
        with lock:
            state = getattr(self, "_state", 0)
            if state:
                _core.state_release(state)
                self._state = 0
            globe = getattr(self, "_globe", 0)
            if globe:
                _core.globe_state_release(globe)
                self._globe = 0

    def __enter__(self):
        with self._lock:
            self._activate()
        return self

    def __exit__(self, *exc_info):
        with self._lock:
            self._activate()
            clear_data()
            _core.state_store()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:  # noqa: BLE001 - never raise from a destructor
            return

    def add_points(self, x, y, z, weights=None, name="points"):
        """Register points from arrays without an intermediate user file."""
        result = _core.add_points_array(x, y, z, name)
        if weights is not None:
            pnts_set_weights(name, list(weights))
        return result

    def add_curves(self, x, y, name="curves"):
        """Register a 2D polyline from arrays."""
        return _core.add_curves_array(x, y, name)

    def add_areas(self, x, y, name="areas"):
        """Register one polygon from arrays."""
        return _core.add_areas_array(x, y, name)

    def add_contours(self, x, y, z, name="contours"):
        """Register a 3D contour polyline from arrays."""
        return _core.add_contours_array(x, y, z, name)

    def read_areas(self, path, name):
        """Loads polygon areas from a text file under the given name."""
        return area_read(path, name)

    def read_points(self, path, name, weights=None, **columns):
        """Loads scattered points from a columned text file.

        Extra keyword arguments are passed on to :func:`pnts_read`, so
        ``columns=...`` maps to col1..col4, delimiter, skip_lines.

        ``weights`` is an optional sequence with one positive value per point;
        without it every point has weight 1.  Points that share a grid cell are
        averaged with these weights.
        """
        result = pnts_read(path, name, **columns)
        if weights is not None and not pnts_set_weights(name, list(weights)):
            raise ValueError(
                "read_points: %r has %d weights, not one per point"
                % (name, len(weights)))
        return result

    def read_curves(self, path, name):
        """Loads 2D curves from a columned text file."""
        return curv_read(path, name)

    def read_contours(self, path, name):
        """Loads 3D contours from a columned text file."""
        return cntr_read(path, name)

    def grid(self, start_x, end_x, step_x, start_y, end_y, step_y, name=None):
        """Creates the target grid; all rules are defined on it."""
        return grid_get(start_x, end_x, step_x, start_y, end_y, step_y, name)

    def grid_auto(self, step_x=0, step_y=0, percent=2, name=None):
        """Creates the target grid over the bounds of the loaded data.

        This is the Tcl ``grid`` command; :meth:`grid` is ``grid_get``.  With
        no step the grid is 255 cells across, and `percent` widens the data
        bounds by that much before the grid is fitted.
        """
        return self._call(_core.grid, step_x, step_y, percent, name)

    def area(self, value, name=_ANY):
        """Rule: the surface equals `value` inside the area.

        `value` may be the string "undef" to leave the area undefined.
        """
        return area(value, name)

    def area_add(self, value, weight, name=_ANY):
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
        """Runs the gridding algorithm.

        ``Session(serial=True)`` forces this task's internal pool to one worker
        for the solve and restores the previous size afterwards.  The pool is
        per task, so other Sessions are unaffected.
        """
        if not self._serial:
            surfit()
            return
        previous = get_threads()
        init_threads(1)
        try:
            surfit()
        finally:
            init_threads(previous)

    def save(self, path, name=_ANY):
        """Saves a surface to a surfit data file."""
        return surf_save(path, name)

    def __getattr__(self, name):
        """Delegates any core command or module helper, so ``task.points(...)``
        works like ``points(...)`` and ``task.surf_names()`` like
        ``surf_names()``.

        Every command is reachable without listing it here, and the Session
        stays in step with the bindings as they grow.
        """
        target = globals().get(name)
        if not name.startswith(_PRIVATE_PREFIX) and callable(target):
            return functools.partial(self._call, target)
        raise AttributeError("%r object has no attribute %r"
                             % (type(self).__name__, name))

    def names(self):
        """Names of the surfaces in memory."""
        return surf_names()

    def surf_index(self, pattern=_ANY):
        """Index of the first surface matching `pattern`, or -1."""
        return surf_index(pattern)

    def values(self, pattern=None):
        """Values of a surface; without a pattern, the most recent one."""
        return values(pattern)

    def residuals(self, x, y, z, weights=None, surface=None):
        """Residual statistics of sample points against the result."""
        return _session_residuals(self, x, y, z, weights, surface)

    def outliers(self, x, y, z, weights=None, surface=None, threshold=3.5):
        """Flags residuals farther than ``threshold`` MADs from the median."""
        return _session_outliers(self, x, y, z, weights, surface, threshold)

    def quality_attributes(self, x, y, weights=None, surface=None):
        """Per-node support: sample count, weights and distances to data."""
        position = (_core.surf_count() - 1 if surface is None
                    else self.surf_index(surface))
        if position < 0:
            raise KeyError("no surface matches %r" % (surface,))
        attributes = cell_attributes(self.values(surface),
                                     _core.surf_extent(position),
                                     x, y, weights)
        attributes["extent"] = _core.surf_extent(position)
        return attributes

    def diagnostic_points(self, x, y, z, weights=None, surface=None,
                          threshold=3.5):
        """Typed point diagnostics (used/outlier/undefined/outside/zero)."""
        position = (_core.surf_count() - 1 if surface is None
                    else self.surf_index(surface))
        if position < 0:
            raise KeyError("no surface matches %r" % (surface,))
        return diagnostic_points(self.values(surface),
                                 _core.surf_extent(position),
                                 x, y, z, weights, threshold)

    def save_diagnostics(self, path, x, y, z, weights=None, surface=None,
                         threshold=3.5):
        """Write typed point diagnostics as GeoJSON or CSV."""
        import csv
        import json

        document = self.diagnostic_points(x, y, z, weights, surface,
                                          threshold)
        if str(path).lower().endswith((".geojson", ".json")):
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(diagnostics_to_geojson(document), stream, indent=2)
                stream.write("\n")
            return path
        if str(path).lower().endswith(".csv"):
            names = ("x", "y", "z", "residual", "predicted", "weight",
                     "scale", "scaled_residual", "code")
            with open(path, "w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(names)
                for index in range(document["x"].size):
                    writer.writerow([
                        document["x"][index], document["y"][index],
                        document["z"][index], document["residual"][index],
                        document["predicted"][index],
                        document["weights"][index], document["scale"][index],
                        document["scaled_residual"][index],
                        document["code"][index],
                    ])
            return path
        raise ValueError("diagnostics path must end in .geojson/.json or .csv")

    def report(self, x, y, z, weights=None, surface=None, threshold=3.5,
               sources=None):
        """Returns a JSON-ready quality summary for the latest surface.

        ``sources`` is an optional path or path -> SHA-256 mapping.  It is
        recorded under ``provenance.sources``; pass relative names if the
        report will be published.
        """
        return quality_report(self, x, y, z, weights, surface, threshold,
                              sources)

    def save_geotiff(self, path, crs=None, surface=None, metadata=None):
        """Writes the latest surface as a GeoTIFF (GDAL optional).

        Without an explicit ``crs`` the task's metadata ``crs`` is used.  The
        optional ``metadata`` mapping is written as GDAL dataset metadata.
        """
        if surface is None:
            position = _core.surf_count() - 1
        else:
            position = self.surf_index(surface)
        if position < 0:
            raise KeyError("no surface matches %r" % (surface,))
        if crs is None:
            crs = self._metadata.get("crs")
        if metadata is None:
            metadata = self._metadata
        return save_geotiff(path, self.values(surface),
                            _core.surf_extent(position), crs,
                            metadata=metadata)

    def save_report(self, path, x, y, z, weights=None, surface=None,
                    threshold=3.5, sources=None):
        """Writes the quality summary as JSON next to the map."""
        import json

        document = quality_report(self, x, y, z, weights, surface, threshold,
                                  sources)
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return path

    def viewer(self, **kwargs):
        """Self-contained HTML page for the result surface."""
        return viewer(**kwargs)

    def save_viewer(self, path, **kwargs):
        """Writes that page to ``path``."""
        return save_viewer(path, **kwargs)


def _reexport_commands():
    """Makes every compiled command available under its Tcl name.

    Names already defined above win, so the richer Python helpers stay in
    place while the plain command wrappers are re-exported wholesale.
    """
    taken = set(globals())
    for name in dir(_core):
        if name.startswith(_PRIVATE_PREFIX) or name in taken:
            continue
        globals()[name] = getattr(_core, name)


def _activating(function):
    """Wraps a Session method so it installs the task's state first.

    The whole activate-and-call pair is under the task's lock: another call on
    the same Session must not use its state between the two steps.  Other
    Sessions in other threads are independent, because the engine's globals
    are thread-local.
    """
    @functools.wraps(function)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            self._activate()
            result = function(self, *args, **kwargs)
            _core.state_store()
            return result
    return wrapper


def _wrap_session_methods():
    """Applies the state switch to every public Session method.

    Doing it here rather than by hand means a method added later cannot forget
    the wrapper.
    """
    for method_name, method in list(vars(Session).items()):
        if not method_name.startswith(_PRIVATE_PREFIX) and callable(method):
            setattr(Session, method_name, _activating(method))


_wrap_session_methods()
_reexport_commands()

from surfit.postgis import read_postgis  # noqa: E402  (after the core re-exports)
from surfit.diagnostics import (  # noqa: E402
    _session_outliers, _session_residuals, bootstrap_uncertainty,
    calibrated_interval, cell_attributes, conformal_quantile,
    coverage_by_group, diagnostic_points, diagnostics_to_geojson, ensemble,
    group_conformal_quantiles, interval_coverage, outlier_mask,
    point_residuals, quality_report)
from surfit.geotiff import (  # noqa: E402
    read_geotiff, save_geotiff, save_geotiff_stack)
from surfit.cross_validation import (  # noqa: E402
    block_labels, cross_validate, fold_assignment)
from surfit.variogram import (  # noqa: E402
    anisotropy, experimental_variogram, fit_variogram)
from surfit.provenance import file_sha256, source_hashes  # noqa: E402
from surfit.sampling import (  # noqa: E402
    decluster, decluster_points, voronoi_weights)
from surfit.crs import (  # noqa: E402
    is_geographic_crs, require_projected, to_crs, transform_extent)
from surfit.padding import crop_surface, pad_extent  # noqa: E402
from surfit.resolution import (  # noqa: E402
    estimate_psf, psf_report, resolution_report)
from surfit.smoothing import select_parameter  # noqa: E402
from surfit.tiled import (  # noqa: E402
    select_geometries, solve_tiled, tile_boxes)
from surfit.stack import SurfaceStack  # noqa: E402
from surfit.benchmark import benchmark_stack  # noqa: E402
