"""Ordered layered surfaces as one small orchestration object.

A stack does not add a solver.  Each layer is built by a callback that returns
a solved Session; the stack checks that the layers share a grid, solves them in
order, and reports crossings, thickness and pinch-outs.  A layer is independent
otherwise, so the existing Session API remains the primitive.
"""

import numpy as np

from surfit import _surfit as _core

_UNDEF = float(np.finfo(np.float32).max)


def _defined(values):
    return ~np.isclose(values, _UNDEF, rtol=1e-6)


def _extent_of(task):
    position = int(task.surf_count()) - 1
    if position < 0:
        raise ValueError("layer build() returned a task without a surface")
    return _core.surf_extent(position)


def _same_extent(first, second):
    keys = ("min_x", "max_x", "min_y", "max_y", "step_x", "step_y",
            "count_x", "count_y")
    return all(np.isclose(float(first[key]), float(second[key]))
               for key in keys)


class SurfaceStack:
    """A named, ordered set of surfaces on one grid."""

    def __init__(self, name="stack"):
        self._name = name
        self._map_name = name
        self._layers = []
        self._tasks = []
        self._values = []
        self._extent = None

    def add_layer(self, name, build):
        """Add a layer; ``build()`` returns a solved or solvable Session."""
        if not callable(build):
            raise TypeError("build must be callable")
        if any(str(name) == existing for existing, _ in self._layers):
            raise ValueError("duplicate layer %r" % (name,))
        self._layers.append((str(name), build))
        return self

    def layer_names(self):
        return [name for name, _ in self._layers]

    def solve(self):
        """Build and solve every layer, checking the shared grid."""
        if not self._layers:
            raise ValueError("a stack needs at least one layer")
        tasks = []
        values = []
        extent = None
        try:
            for name, build in self._layers:
                task = build()
                if not hasattr(task, "values"):
                    raise TypeError(
                        "layer %r build() must return a Session" % (name,))
                if hasattr(task, "solve"):
                    task.solve()
                layer_values = np.asarray(task.values(), dtype=float)
                layer_extent = _extent_of(task)
                if extent is None:
                    extent = layer_extent
                elif not _same_extent(extent, layer_extent):
                    raise ValueError("layer %r does not share the stack grid"
                                     % (name,))
                tasks.append(task)
                values.append(layer_values)
        except Exception:
            for task in tasks:
                close = getattr(task, "close", None)
                if close is not None:
                    close()
            raise
        self._tasks = tasks
        self._values = values
        self._extent = extent
        return self

    def values(self, name=None):
        """Return one layer array, or a name -> array mapping."""
        if not self._values:
            raise RuntimeError("solve() the stack first")
        if name is None:
            return {layer: value for (layer, _), value in
                    zip(self._layers, self._values)}
        for (layer, _), value in zip(self._layers, self._values):
            if layer == name:
                return value
        raise KeyError("unknown layer %r" % (name,))

    def report(self):
        """JSON-ready crossings, thickness and pinch-out summary."""
        if not self._values:
            raise RuntimeError("solve() the stack first")
        report = {"name": self._name, "layers": [], "crossings": 0,
                  "thickness": []}
        for index, ((name, _), values) in enumerate(
                zip(self._layers, self._values)):
            defined = _defined(values)
            item = {
                "name": name,
                "defined": int(defined.sum()),
                "total": int(defined.size),
            }
            report["layers"].append(item)
            if index == len(self._values) - 1:
                continue
            below = self._values[index + 1]
            both = defined & _defined(below)
            thickness = values - below
            crossing = both & (thickness < 0)
            pinch = both & (thickness <= 0)
            item["thickness"] = {
                "min": float(np.min(thickness[both])) if both.any() else None,
                "max": float(np.max(thickness[both])) if both.any() else None,
                "median": (float(np.median(thickness[both]))
                           if both.any() else None),
                "crossings": int(crossing.sum()),
                "pinchouts": int(pinch.sum()),
            }
            report["crossings"] += int(crossing.sum())
            report["thickness"].append(item["thickness"])
        return report

    def close(self):
        for task in self._tasks:
            close = getattr(task, "close", None)
            if close is not None:
                close()
        self._tasks = []
        self._values = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False
