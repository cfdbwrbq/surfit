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


class StackValidationError(ValueError):
    """Raised by ``SurfaceStack.validate(strict=True)``."""

    def __init__(self, validation):
        self.validation = validation
        messages = [item["message"] for item in validation["violations"]]
        super().__init__("stack validation failed: " + "; ".join(messages))


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
        self._provenance = {}
        self._uncertainty = {}
        self._memmaps = []
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

    def set_layer_provenance(self, name, sources=None, params=None,
                             metadata=None):
        """Attach auditable metadata to a layer.

        ``sources`` maps a source path/name to its SHA-256 (or another stable
        identifier); ``params`` and ``metadata`` are JSON-ready mappings.
        Repeated calls merge into the existing record.
        """
        if name not in self.layer_names():
            raise KeyError("unknown layer %r" % (name,))
        record = self._provenance.setdefault(str(name), {})
        if sources is not None:
            record.setdefault("sources", {}).update(dict(sources))
        if params is not None:
            record.setdefault("params", {}).update(dict(params))
        if metadata is not None:
            record.setdefault("metadata", {}).update(dict(metadata))
        return self

    def provenance(self, name):
        """Return a copy of one layer's provenance record."""
        if name not in self.layer_names():
            raise KeyError("unknown layer %r" % (name,))
        import copy

        return copy.deepcopy(self._provenance.get(str(name), {}))

    def set_layer_uncertainty(self, name, residuals=None, level=0.9,
                              lower=None, upper=None, symmetric=True,
                              coverage=None):
        """Attach a calibrated interval to a solved layer.

        Pass held-out ``residuals`` to calibrate the width, or explicit
        ``lower``/``upper`` arrays.  ``coverage`` is optional caller-reported
        empirical coverage; the stack does not invent it.
        """
        if not self._values:
            raise RuntimeError("solve() the stack first")
        names = self.layer_names()
        if name not in names:
            raise KeyError("unknown layer %r" % (name,))
        if not 0.0 < level < 1.0:
            raise ValueError("level must be between 0 and 1")
        if coverage is not None and not 0.0 <= coverage <= 1.0:
            raise ValueError("coverage must be between 0 and 1")
        index = names.index(name)
        center = self._values[index]
        quantile = None
        if residuals is not None:
            if lower is not None or upper is not None:
                raise ValueError("pass residuals or explicit bounds, not both")
            from surfit.diagnostics import calibrated_interval

            interval = calibrated_interval(
                center, residuals, level=level, symmetric=symmetric)
            lower = interval["lower"]
            upper = interval["upper"]
            quantile = interval["quantile"]
        elif lower is None or upper is None:
            raise ValueError("pass residuals or both lower and upper")
        lower = np.asarray(lower, dtype=float)
        upper = np.asarray(upper, dtype=float)
        if lower.shape != center.shape or upper.shape != center.shape:
            raise ValueError("uncertainty bounds must match the layer shape")
        if np.any(lower > upper):
            raise ValueError("lower bound exceeds upper bound")
        self._uncertainty[str(name)] = {
            "lower": lower,
            "upper": upper,
            "level": float(level),
            "quantile": None if quantile is None else float(quantile),
            "coverage": None if coverage is None else float(coverage),
        }
        return self

    def interval(self, name):
        """Return the calibrated interval for one layer."""
        if name not in self.layer_names():
            raise KeyError("unknown layer %r" % (name,))
        record = self._uncertainty.get(str(name))
        if record is None:
            raise KeyError("layer %r has no uncertainty" % (name,))
        return {
            "lower": record["lower"],
            "upper": record["upper"],
            "center": self._values[self.layer_names().index(str(name))],
            "level": record["level"],
            "quantile": record["quantile"],
            "coverage": record["coverage"],
        }

    def _uncertainty_summary(self, name):
        record = self._uncertainty.get(name)
        if record is None:
            return None
        lower = record["lower"]
        upper = record["upper"]
        width = upper - lower
        finite = np.isfinite(width)
        if not finite.any():
            mean_width = None
            median_width = None
        else:
            mean_width = float(np.mean(width[finite]))
            median_width = float(np.median(width[finite]))
        return {
            "level": record["level"],
            "quantile": record["quantile"],
            "coverage": record["coverage"],
            "mean_width": mean_width,
            "median_width": median_width,
        }

    def _relation_conflicts(self):
        conflicts = []
        for relation in self._relations:
            upper = self._uncertainty.get(relation["upper"])
            lower = self._uncertainty.get(relation["lower"])
            if upper is None or lower is None:
                continue
            margin = relation["min_thickness"]
            mask = (np.isfinite(upper["lower"]) &
                    np.isfinite(lower["upper"]))
            cells = int((mask & (upper["lower"] <
                                 lower["upper"] + margin)).sum())
            conflicts.append({
                "upper": relation["upper"],
                "lower": relation["lower"],
                "min_thickness": margin,
                "cells": cells,
            })
        return conflicts

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
    def extent(self):
        """Copy of the stack extent (min/max/step/counts)."""
        if self._extent is None:
            raise RuntimeError("solve() the stack first")
        return dict(self._extent)


    def _uses_memmap(self):
        return any(isinstance(value, np.memmap) for value in self._values)

    def to_xarray(self):
        """Eager xarray Dataset with layers and calibrated intervals."""
        from surfit.xarray_export import to_xarray as _to_xarray

        return _to_xarray(self)

    def to_zarr(self, path, mode="w", **kwargs):
        """Write the eager Dataset to Zarr (xarray/zarr are optional)."""
        from surfit.xarray_export import to_zarr as _to_zarr

        return _to_zarr(self, path, mode=mode, **kwargs)

    def section(self, path_x, path_y, samples=200, method="bilinear"):
        """Sample all layers and intervals along a polyline."""
        from surfit.sections import stack_section

        return stack_section(self, path_x, path_y, samples=samples,
                             method=method)

    def save(self, directory):
        """Persist the solved stack as .npy layers plus a JSON manifest."""
        import copy
        import json
        import os

        from surfit.provenance import engine_version

        if not self._values:
            raise RuntimeError("solve() the stack first")
        os.makedirs(directory, exist_ok=True)
        layers_dir = os.path.join(directory, "layers")
        os.makedirs(layers_dir, exist_ok=True)
        document = {
            "format": "surfit-surface-stack",
            "version": 1,
            "engine_version": engine_version(),
            "name": self._name,
            "extent": dict(self._extent),
            "layers": [],
            "timings": dict(self._timings),
            "provenance": copy.deepcopy(self._provenance),
            "report": self.report(streaming=self._uses_memmap()),
        }
        for index, ((name, _), values) in enumerate(
                zip(self._layers, self._values)):
            filename = "%03d.npy" % index
            np.save(os.path.join(layers_dir, filename), values,
                    allow_pickle=False)
            item = {"name": name, "file": filename}
            record = self._uncertainty.get(name)
            if record is not None:
                uncertainty_dir = os.path.join(directory, "uncertainty")
                os.makedirs(uncertainty_dir, exist_ok=True)
                lower_name = "%03d_lower.npy" % index
                upper_name = "%03d_upper.npy" % index
                np.save(os.path.join(uncertainty_dir, lower_name),
                        record["lower"], allow_pickle=False)
                np.save(os.path.join(uncertainty_dir, upper_name),
                        record["upper"], allow_pickle=False)
                item["uncertainty"] = {
                    "lower_file": lower_name,
                    "upper_file": upper_name,
                    "level": record["level"],
                    "quantile": record["quantile"],
                    "coverage": record["coverage"],
                }
            document["layers"].append(item)
        with open(os.path.join(directory, "manifest.json"), "w",
                  encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return directory

    @classmethod
    def load(cls, directory, mmap=False):
        """Load a stack written by :meth:`save`.

        With ``mmap=True`` the layer arrays are read-only memory maps; use
        ``close()`` to release them.  A read-only stack cannot be projected
        with ``apply_pinchout``.
        """
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
        stack._provenance = dict(document.get("provenance", {}))
        layers = []
        values = []
        for item in document["layers"]:
            path = os.path.join(directory, "layers", item["file"])
            array = np.load(path, allow_pickle=False,
                            mmap_mode="r" if mmap else None)
            expected = (int(stack._extent["count_y"]),
                        int(stack._extent["count_x"]))
            if array.shape != expected:
                raise ValueError("layer %r has shape %s, expected %s"
                                 % (item["name"], array.shape, expected))
            layers.append((str(item["name"]), None))
            values.append(array)
            record = item.get("uncertainty")
            if record is not None:
                lower = np.load(
                    os.path.join(directory, "uncertainty",
                                 record["lower_file"]),
                    allow_pickle=False,
                    mmap_mode="r" if mmap else None)
                upper = np.load(
                    os.path.join(directory, "uncertainty",
                                 record["upper_file"]),
                    allow_pickle=False,
                    mmap_mode="r" if mmap else None)
                stack._uncertainty[str(item["name"])] = {
                    "lower": lower,
                    "upper": upper,
                    "level": float(record["level"]),
                    "quantile": record.get("quantile"),
                    "coverage": record.get("coverage"),
                }
        stack._layers = layers
        stack._values = values
        stack._tasks = []
        if mmap:
            stack._memmaps = list(values)
        return stack

    def _persist_values(self, values, directory):
        import os

        os.makedirs(directory, exist_ok=True)
        mapped = []
        for index, value in enumerate(values):
            path = os.path.join(directory, "layer_%03d.dat" % index)
            array = np.memmap(path, dtype="float64", mode="w+",
                              shape=value.shape)
            array[:] = value
            array.flush()
            mapped.append(array)
        return mapped

    def _build_layer(self, item):
        name, build = item
        task = build()
        if not hasattr(task, "values"):
            raise TypeError("layer %r build() must return a Session" % (name,))
        if hasattr(task, "solve"):
            task.solve()
        return task

    def solve(self, parallel=False, workers=None, memmap=False,
              memmap_dir=None):
        """Build and solve every layer, checking the shared grid.

        ``parallel=True`` builds/solves independent layers in a thread pool.
        The engine's globals are thread-local, so separate Sessions are safe;
        a callback that shares one Session between layers is not.
        """
        if not self._layers:
            raise ValueError("a stack needs at least one layer")
        if self._relations and parallel:
            raise ValueError("relations require sequential solve")
        if memmap and memmap_dir is None:
            raise ValueError("memmap=True needs memmap_dir")
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
        if memmap:
            mapped = self._persist_values(values, memmap_dir)
            for task in tasks:
                close = getattr(task, "close", None)
                if close is not None:
                    close()
            tasks = []
            values = mapped
            self._memmaps = mapped
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

    def validate(self, max_crossings=0, min_thickness=None,
                 min_coverage=None, max_relation_conflicts=None,
                 strict=False):
        """Check the solved stack against explicit thresholds.

        Returns ``{"ok", "violations", "report", "thresholds"}``.  With
        ``strict=True`` a violation raises :class:`StackValidationError`; the
        exception carries the same result.  This is a policy check over the
        report, not a solver repair.
        """
        if not isinstance(max_crossings, int) or max_crossings < 0:
            raise ValueError("max_crossings must be a non-negative integer")
        if min_thickness is not None and not np.isfinite(min_thickness):
            raise ValueError("min_thickness must be finite or None")
        if min_coverage is not None and not 0.0 <= min_coverage <= 1.0:
            raise ValueError("min_coverage must be between 0 and 1")
        if max_relation_conflicts is not None and (
                not isinstance(max_relation_conflicts, int) or
                max_relation_conflicts < 0):
            raise ValueError(
                "max_relation_conflicts must be a non-negative integer")
        report = self.report(streaming=self._uses_memmap())
        violations = []
        if report["crossings"] > max_crossings:
            violations.append({
                "code": "crossings",
                "value": int(report["crossings"]),
                "limit": int(max_crossings),
                "message": "crossings %d exceed %d"
                           % (report["crossings"], max_crossings),
            })
        if max_relation_conflicts is not None:
            for conflict in report["relation_conflicts"]:
                if conflict["cells"] > max_relation_conflicts:
                    violations.append({
                        "code": "relation_conflict",
                        "upper": conflict["upper"],
                        "lower": conflict["lower"],
                        "value": int(conflict["cells"]),
                        "limit": int(max_relation_conflicts),
                        "message": "relation %r >= %r has %d uncertain "
                                   "conflicts"
                                   % (conflict["upper"], conflict["lower"],
                                      conflict["cells"]),
                    })
        for item in report["layers"]:
            if min_coverage is not None and item["coverage"] < min_coverage:
                violations.append({
                    "code": "coverage",
                    "layer": item["name"],
                    "value": item["coverage"],
                    "limit": float(min_coverage),
                    "message": "layer %r coverage %.3f is below %.3f"
                               % (item["name"], item["coverage"],
                                  min_coverage),
                })
            if min_thickness is None or "thickness" not in item:
                continue
            value = item["thickness"]["min"]
            if value is None:
                violations.append({
                    "code": "thickness",
                    "layer": item["name"],
                    "value": None,
                    "limit": float(min_thickness),
                    "message": "layer %r has no finite thickness"
                               % (item["name"],),
                })
            elif value < min_thickness:
                violations.append({
                    "code": "thickness",
                    "layer": item["name"],
                    "value": float(value),
                    "limit": float(min_thickness),
                    "message": "layer %r thickness %.3f is below %.3f"
                               % (item["name"], value, min_thickness),
                })
        validation = {
            "ok": not violations,
            "violations": violations,
            "report": report,
            "thresholds": {
                "max_crossings": int(max_crossings),
                "min_thickness": (None if min_thickness is None
                                  else float(min_thickness)),
                "min_coverage": (None if min_coverage is None
                                 else float(min_coverage)),
                "max_relation_conflicts": (
                    None if max_relation_conflicts is None
                    else int(max_relation_conflicts)),
            },
        }
        if strict and violations:
            raise StackValidationError(validation)
        return validation

    def _streaming_report(self, chunk_rows=None):
        """Build the report in bounded row chunks.

        Min/max/crossings/pinch-outs are exact.  The median comes from a
        4096-bin histogram over the observed thickness range, so it is
        deterministic but approximate; ``median_exact`` is false.
        """
        if not self._values:
            raise RuntimeError("solve() the stack first")
        count_y, count_x = self._values[0].shape
        if chunk_rows is None:
            chunk_rows = max(1, 4000000 // max(1, count_x * 8))
        chunk_rows = min(int(chunk_rows), count_y)
        report = {"name": self._name, "layers": [], "crossings": 0,
                  "thickness": [], "seconds": self._timings.get("seconds"),
                  "streaming": True, "chunk_rows": chunk_rows}
        for index, ((name, _), values) in enumerate(
                zip(self._layers, self._values)):
            defined_count = 0
            for start in range(0, count_y, chunk_rows):
                stop = min(start + chunk_rows, count_y)
                defined_count += int(_defined(values[start:stop]).sum())
            item = {
                "name": name,
                "defined": defined_count,
                "total": int(count_y * count_x),
                "coverage": (float(defined_count) / float(count_y * count_x)
                             if count_y * count_x else 0.0),
            }
            report["layers"].append(item)
            if index == len(self._values) - 1:
                continue
            below = self._values[index + 1]
            both_count = 0
            crossings = 0
            pinchouts = 0
            minimum = None
            maximum = None
            for start in range(0, count_y, chunk_rows):
                stop = min(start + chunk_rows, count_y)
                upper_chunk = values[start:stop]
                lower_chunk = below[start:stop]
                both = _defined(upper_chunk) & _defined(lower_chunk)
                if not both.any():
                    continue
                thickness = upper_chunk[both] - lower_chunk[both]
                both_count += int(both.sum())
                crossings += int((thickness < 0).sum())
                pinchouts += int((thickness <= 0).sum())
                chunk_min = float(thickness.min())
                chunk_max = float(thickness.max())
                minimum = chunk_min if minimum is None else min(minimum,
                                                                 chunk_min)
                maximum = chunk_max if maximum is None else max(maximum,
                                                                 chunk_max)
            median = None
            median_exact = True
            if both_count:
                if minimum == maximum:
                    median = minimum
                else:
                    edges = np.linspace(minimum, maximum, 4097)
                    histogram = np.zeros(4096, dtype=np.int64)
                    for start in range(0, count_y, chunk_rows):
                        stop = min(start + chunk_rows, count_y)
                        upper_chunk = values[start:stop]
                        lower_chunk = below[start:stop]
                        both = _defined(upper_chunk) & _defined(lower_chunk)
                        if both.any():
                            thickness = upper_chunk[both] - lower_chunk[both]
                            histogram += np.histogram(thickness, bins=edges)[0]
                    cumulative = np.cumsum(histogram)
                    position = (both_count + 1) // 2
                    bin_index = min(int(np.searchsorted(cumulative, position)),
                                    histogram.size - 1)
                    median = float((edges[bin_index] +
                                    edges[bin_index + 1]) / 2.0)
                    median_exact = False
            item["thickness"] = {
                "min": minimum,
                "max": maximum,
                "median": median,
                "crossings": crossings,
                "pinchouts": pinchouts,
                "median_exact": median_exact,
            }
            item["uncertainty"] = self._uncertainty_summary(name)
            report["crossings"] += crossings
            report["thickness"].append(item["thickness"])
        report["relation_conflicts"] = self._relation_conflicts()
        return report

    def report(self, streaming=False):
        """JSON-ready crossings, thickness and pinch-out summary.

        ``streaming=True`` uses row chunks and a histogram median; it is the
        intended mode for memory-mapped stacks.
        """
        if streaming:
            return self._streaming_report()
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
                "coverage": (float(defined.sum()) / float(defined.size)
                             if defined.size else 0.0),
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
            item["uncertainty"] = self._uncertainty_summary(name)
            report["crossings"] += int(crossing.sum())
            report["thickness"].append(item["thickness"])
        report["relation_conflicts"] = self._relation_conflicts()
        return report

    def close(self):
        for task in self._tasks:
            close = getattr(task, "close", None)
            if close is not None:
                close()
        for array in self._memmaps:
            array.flush()
            mapping = getattr(array, "_mmap", None)
            if mapping is not None:
                mapping.close()
        self._memmaps = []
        self._tasks = []
        self._values = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False
