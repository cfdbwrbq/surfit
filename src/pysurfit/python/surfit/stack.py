"""Ordered layered surfaces as one small orchestration object.

A stack does not add a solver.  Each layer is built by a callback that returns
a solved Session; the stack checks that the layers share a grid, solves them in
order, and reports crossings, thickness and pinch-outs.  A layer is independent
otherwise, so the existing Session API remains the primitive.
"""

import time

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

    def apply(self, task, name="__stack_relation"):
        """Add the relation to an *unsolved* task before its next functional."""
        shifted = self.values + self.min_thickness
        shifted[~_defined(self.values)] = _UNDEF
        task.add_surface(shifted, self.extent["min_x"], self.extent["step_x"],
                         self.extent["min_y"], self.extent["step_y"], name)
        task.surface_geq(name, self.penalty)


class SurfaceRelations:
    """All inter-surface conditions that apply to one layer."""

    def __init__(self, relations):
        self.relations = list(relations)

    def apply(self, task):
        for index, relation in enumerate(self.relations):
            relation.apply(task, "__stack_relation_%d" % index)


class SurfaceStack:
    """A named, ordered set of surfaces on one grid."""

    def __init__(self, name="stack"):
        self._name = name
        self._map_name = name
        self._layers = []
        self._relations = []
        self._tasks = []
        self._values = []
        self._timings = {}
        self._extent = None

    def add_layer(self, name, build, above=None, below=None,
                  min_thickness=0.0, penalty=0.0):
        """Add a layer; ``build()`` returns a Session.

        ``above`` means ``this >= named + min_thickness``; ``below`` means
        ``this <= named - min_thickness``.  A constrained builder receives a
        ``SurfaceRelations`` object and must call ``relations.apply(task)``
        before its next functional (for example before the points rule).  A
        builder that does not accept the relation argument raises a clear
        error, not a silently ignored condition.
        """
        if not callable(build):
            raise TypeError("build must be callable")
        if any(str(name) == existing for existing, _ in self._layers):
            raise ValueError("duplicate layer %r" % (name,))
        if above is not None:
            self.add_relation(str(name), str(above), min_thickness, penalty)
        if below is not None:
            self.add_relation(str(below), str(name), min_thickness, penalty)
        self._layers.append((str(name), build))
        return self

    def add_relation(self, upper, lower, min_thickness=0.0, penalty=0.0):
        """Constrain ``upper >= lower + min_thickness``.

        The relation may refer to layers added later; it is resolved by the
        topological solve, not by add order.
        """
        self._relations.append({
            "upper": str(upper),
            "lower": str(lower),
            "min_thickness": float(min_thickness),
            "penalty": float(penalty),
        })
        return self

    def _topological_order(self):
        names = self.layer_names()
        incoming = {name: 0 for name in names}
        outgoing = {name: [] for name in names}
        for relation in self._relations:
            upper = relation["upper"]
            lower = relation["lower"]
            if upper not in incoming or lower not in incoming:
                raise ValueError(
                    "relation %r -> %r names an unknown layer"
                    % (upper, lower))
            outgoing[lower].append(upper)
            incoming[upper] += 1
        ready = [name for name in names if incoming[name] == 0]
        ordered = []
        while ready:
            name = ready.pop(0)
            ordered.append(name)
            for upper in outgoing[name]:
                incoming[upper] -= 1
                if incoming[upper] == 0:
                    ready.append(upper)
        if len(ordered) != len(names):
            raise ValueError("relation graph contains a cycle")
        return ordered

    def layer_names(self):
        return [name for name, _ in self._layers]

    def save(self, directory):
        """Persist the solved stack as .npy layers plus a JSON manifest."""
        import json
        import os

        if not self._values:
            raise RuntimeError("solve() the stack first")
        os.makedirs(directory, exist_ok=True)
        layers_dir = os.path.join(directory, "layers")
        os.makedirs(layers_dir, exist_ok=True)
        document = {
            "format": "surfit-surface-stack",
            "version": 1,
            "name": self._name,
            "extent": dict(self._extent),
            "layers": [],
            "timings": dict(self._timings),
            "report": self.report(),
        }
        for index, ((name, _), values) in enumerate(
                zip(self._layers, self._values)):
            filename = "%03d.npy" % index
            np.save(os.path.join(layers_dir, filename), values,
                    allow_pickle=False)
            document["layers"].append({"name": name, "file": filename})
        with open(os.path.join(directory, "manifest.json"), "w",
                  encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return directory

    @classmethod
    def load(cls, directory):
        """Load a stack written by :meth:`save`; layers are read-only arrays."""
        import json
        import os

        manifest_path = os.path.join(directory, "manifest.json")
        with open(manifest_path, encoding="utf-8") as stream:
            document = json.load(stream)
        if document.get("format") != "surfit-surface-stack":
            raise ValueError("not a surfit surface stack: %s" % (directory,))
        if int(document.get("version", 0)) != 1:
            raise ValueError("unsupported stack version")
        stack = cls(document.get("name", "stack"))
        stack._extent = dict(document["extent"])
        stack._timings = dict(document.get("timings", {}))
        layers = []
        values = []
        for item in document["layers"]:
            path = os.path.join(directory, "layers", item["file"])
            array = np.load(path, allow_pickle=False)
            expected = (int(stack._extent["count_y"]),
                        int(stack._extent["count_x"]))
            if array.shape != expected:
                raise ValueError("layer %r has shape %s, expected %s"
                                 % (item["name"], array.shape, expected))
            layers.append((str(item["name"]), None))
            values.append(array)
        stack._layers = layers
        stack._values = values
        stack._tasks = []
        return stack

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
        started = time.perf_counter()
        tasks = []
        try:
            if self._relations:
                solved = {}
                result = {}
                builders = dict(self._layers)
                for name in self._topological_order():
                    relations = [
                        SurfaceRelation(
                            solved[item["lower"]][0],
                            solved[item["lower"]][1],
                            item["min_thickness"], item["penalty"])
                        for item in self._relations if item["upper"] == name
                    ]
                    if relations:
                        try:
                            task = builders[name](SurfaceRelations(relations))
                        except TypeError as error:
                            raise TypeError(
                                "layer %r with a relation must accept "
                                "relations in build(relations)" % (name,)) from error
                    else:
                        task = builders[name]()
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
                        self._layers, values,
                        [result[n][2] for n, _ in self._layers]):
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
        self._timings = {"seconds": time.perf_counter() - started}
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

    def apply_pinchout(self, name, threshold=0.0, mode="merge"):
        """Apply an explicit post-solve pinch-out to the named layer.

        ``mode="merge"`` sets the upper layer to the lower value (zero
        thickness); ``mode="undef"`` marks the upper cells undefined.  This is
        a projection after the solve, not a hidden solver constraint.
        """
        if mode not in ("merge", "undef"):
            raise ValueError("mode must be 'merge' or 'undef'")
        names = self.layer_names()
        if name not in names:
            raise KeyError("unknown layer %r" % (name,))
        index = names.index(name)
        if index == len(names) - 1:
            raise ValueError("the last layer has no next layer")
        mask = self.pinchout_mask(name, threshold)
        if mode == "merge":
            self._values[index][mask] = self._values[index + 1][mask]
        else:
            self._values[index][mask] = _UNDEF
        return int(mask.sum())

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
                  "thickness": [], "seconds": self._timings.get("seconds")}
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
