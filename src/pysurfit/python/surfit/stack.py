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


class SurfaceRelation:
    """A condition passed to a layer builder for an inter-surface relation."""

    def __init__(self, values, extent, min_thickness=0.0, penalty=0.0):
        self.values = np.asarray(values, dtype=float)
        self.extent = dict(extent)
        self.min_thickness = float(min_thickness)
        self.penalty = float(penalty)

    def apply(self, task):
        """Add the relation to an *unsolved* task before its next functional."""
        shifted = self.values + self.min_thickness
        shifted[~_defined(self.values)] = _UNDEF
        task.add_surface(shifted, self.extent["min_x"], self.extent["step_x"],
                         self.extent["min_y"], self.extent["step_y"],
                         "__stack_relation")
        task.surface_geq("__stack_relation", self.penalty)


class SurfaceStack:
    """A named, ordered set of surfaces on one grid."""

    def __init__(self, name="stack"):
        self._name = name
        self._map_name = name
        self._layers = []
        self._relations = {}
        self._tasks = []
        self._values = []
        self._extent = None

    def add_layer(self, name, build, above=None, min_thickness=0.0,
                  penalty=0.0):
        """Add a layer; ``build()`` returns a Session.

        ``above`` names a layer lower in the stack.  The stack solves
        bottom-up and calls ``build(relation)`` for the constrained layer; the
        callback must call ``relation.apply(task)`` before its next functional
        (for example before the points rule).  ``this >= lower + min_thickness``.
        A builder that does not accept the relation argument raises a clear
        error rather than silently ignoring the condition.
        """
        if not callable(build):
            raise TypeError("build must be callable")
        if any(str(name) == existing for existing, _ in self._layers):
            raise ValueError("duplicate layer %r" % (name,))
        if above is not None:
            if str(above) in [str(item) for item, _ in self._layers]:
                raise ValueError("relation target %r must be added later" % (above,))
            self._relations[str(name)] = {
                "target": str(above),
                "min_thickness": float(min_thickness),
                "penalty": float(penalty),
            }
        self._layers.append((str(name), build))
        return self

    def layer_names(self):
        return [name for name, _ in self._layers]

    def _build_layer(self, item):
        name, build = item
        task = build()
        if not hasattr(task, "values"):
            raise TypeError("layer %r build() must return a Session" % (name,))
        if hasattr(task, "solve"):
            task.solve()
        return task

    def solve(self, parallel=False, workers=None):
        """Build and solve every layer, checking the shared grid.

        ``parallel=True`` builds/solves independent layers in a thread pool.
        The engine's globals are thread-local, so separate Sessions are safe;
        a callback that shares one Session between layers is not.
        """
        if not self._layers:
            raise ValueError("a stack needs at least one layer")
        if self._relations and parallel:
            raise ValueError("relations require sequential solve")
        tasks = []
        try:
            if self._relations:
                solved = {}
                ordered = list(reversed(self._layers))
                result = {}
                for name, build in ordered:
                    relation_spec = self._relations.get(name)
                    if relation_spec is not None:
                        target = relation_spec["target"]
                        if target not in solved:
                            raise ValueError(
                                "relation target %r is not solved" % (target,))
                        relation = SurfaceRelation(
                            solved[target][0], solved[target][1],
                            relation_spec["min_thickness"],
                            relation_spec["penalty"])
                        try:
                            task = build(relation)
                        except TypeError as error:
                            raise TypeError(
                                "layer %r with a relation must accept "
                                "relation in build(relation)" % (name,)) from error
                    else:
                        task = build()
                    if not hasattr(task, "values"):
                        raise TypeError(
                            "layer %r build() must return a Session" % (name,))
                    task.solve()
                    layer_values = np.asarray(task.values(), dtype=float)
                    layer_extent = _extent_of(task)
                    solved[name] = (layer_values, layer_extent)
                    result[name] = (task, layer_values, layer_extent)
                tasks = [result[name][0] for name, _ in self._layers]
                values = [result[name][1] for name, _ in self._layers]
                extent = result[self._layers[-1][0]][2]
                for (name, _), value, layer_extent in zip(
                        self._layers, values, [result[n][2] for n, _ in self._layers]):
                    if not _same_extent(extent, layer_extent):
                        raise ValueError("layer %r does not share the stack grid"
                                         % (name,))
            else:
                if parallel:
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        tasks = list(pool.map(self._build_layer, self._layers))
                else:
                    tasks = [self._build_layer(item) for item in self._layers]
                values = []
                extent = None
                for (name, _), task in zip(self._layers, tasks):
                    layer_values = np.asarray(task.values(), dtype=float)
                    layer_extent = _extent_of(task)
                    if extent is None:
                        extent = layer_extent
                    elif not _same_extent(extent, layer_extent):
                        raise ValueError("layer %r does not share the stack grid"
                                         % (name,))
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

    def thickness(self, name):
        """Thickness to the next layer; NaN where either side is undefined."""
        if not self._values:
            raise RuntimeError("solve() the stack first")
        names = self.layer_names()
        if name not in names:
            raise KeyError("unknown layer %r" % (name,))
        index = names.index(name)
        if index == len(names) - 1:
            raise ValueError("the last layer has no next layer")
        upper = self._values[index]
        lower = self._values[index + 1]
        both = _defined(upper) & _defined(lower)
        result = np.full(upper.shape, np.nan)
        result[both] = upper[both] - lower[both]
        return result

    def pinchout_mask(self, name, threshold=0.0):
        """Boolean cells where the layer is absent/non-positive thickness."""
        thickness = self.thickness(name)
        return np.isfinite(thickness) & (thickness <= float(threshold))

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
