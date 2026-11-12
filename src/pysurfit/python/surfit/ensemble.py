"""Coherent surface ensembles and arithmetic.

An ensemble is a sequence of surface realizations.  Operations are elementwise
across the *same* realization index, so differences and percentiles are
coherent; this is not the same as combining per-cell interval bounds.
"""

import numpy as np


class SurfaceEnsemble:
    """A set of coherent named surfaces."""

    def __init__(self, realizations, extent=None, name=None):
        if not realizations:
            raise ValueError("at least one realization is required")
        layers = {}
        for realization in realizations:
            if not isinstance(realization, dict):
                raise TypeError("each realization must be a name -> array mapping")
            for layer_name, values in realization.items():
                array = np.asarray(values, dtype=float)
                layers.setdefault(layer_name, []).append(array)
        shapes = {array.shape for values in layers.values() for array in values}
        if len(shapes) != 1:
            raise ValueError("all realizations must share one grid shape")
        self._layers = {key: np.stack(values) for key, values in layers.items()}
        self.extent = None if extent is None else dict(extent)
        self.name = name

    @classmethod
    def from_stacks(cls, stacks):
        """Build an ensemble from solved SurfaceStacks with the same layers."""
        stacks = list(stacks)
        if not stacks:
            raise ValueError("at least one stack is required")
        names = stacks[0].layer_names()
        for stack in stacks:
            if stack.layer_names() != names:
                raise ValueError("stacks must have the same layer order")
        realizations = []
        for stack in stacks:
            realizations.append({name: stack.values(name) for name in names})
        return cls(realizations, extent=stacks[0].extent(), name=stacks[0]._name)

    @property
    def size(self):
        return next(iter(self._layers.values())).shape[0]

    @property
    def layers(self):
        return dict(self._layers)

    def __getitem__(self, name):
        return self._layers[name]

    def _binary(self, other, operator, name=None):
        if isinstance(other, SurfaceEnsemble):
            if set(self._layers) != set(other._layers):
                raise ValueError("ensembles must have the same layers")
            if self.size != other.size:
                raise ValueError("ensembles must have the same size")
            layers = {key: operator(self._layers[key], other._layers[key])
                      for key in self._layers}
            return SurfaceEnsemble(
                [{key: layers[key][i] for key in layers}
                 for i in range(self.size)],
                extent=self.extent, name=name or self.name)
        layers = {key: operator(values, other)
                  for key, values in self._layers.items()}
        return SurfaceEnsemble(
            [{key: layers[key][i] for key in layers}
             for i in range(self.size)],
            extent=self.extent, name=name or self.name)

    def __add__(self, other):
        return self._binary(other, np.add)

    def __sub__(self, other):
        return self._binary(other, np.subtract)

    def __mul__(self, other):
        return self._binary(other, np.multiply)

    def __truediv__(self, other):
        return self._binary(other, np.divide)

    def percentiles(self, levels=(10, 50, 90)):
        """Per-layer percentile surfaces; keys are ``p10``/``p50``/``p90``."""
        levels = [float(level) for level in levels]
        if any(not 0.0 <= level <= 100.0 for level in levels):
            raise ValueError("levels must be between 0 and 100")
        result = {}
        for level in levels:
            result["p%g" % level] = {
                key: np.percentile(values, level, axis=0)
                for key, values in self._layers.items()}
        return result

    def mean(self):
        return {key: values.mean(axis=0) for key, values in self._layers.items()}

    def std(self):
        return {key: values.std(axis=0) for key, values in self._layers.items()}

    def volume_between(self, lower, extent, mask=None):
        """Volume between this ensemble and a lower ensemble/scalar/level."""
        if self.extent is not None:
            extent = self.extent
        area = float(extent["step_x"]) * float(extent["step_y"])
        if isinstance(lower, SurfaceEnsemble):
            if set(self._layers) != set(lower._layers):
                raise ValueError("ensembles must have the same layers")
            lower_values = lower._layers
        else:
            lower_values = None
        volumes = {}
        for name, values in self._layers.items():
            if lower_values is None:
                lower_array = np.asarray(lower, dtype=float)
            else:
                lower_array = lower_values[name]
            thickness = values - lower_array
            if mask is not None:
                mask_array = np.asarray(mask, dtype=bool)
                thickness = np.where(mask_array, thickness, np.nan)
            volumes[name] = np.nansum(thickness, axis=(1, 2)) * area
        return volumes

    def isochore(self, level, extent, above=True):
        """Per-realization area and volume for values above/below a level."""
        area = float(extent["step_x"]) * float(extent["step_y"])
        result = {}
        for name, values in self._layers.items():
            if above:
                selected = values >= level
                thickness = values - level
            else:
                selected = values <= level
                thickness = level - values
            result[name] = {
                "area": selected.sum(axis=(1, 2)) * area,
                "volume": np.nansum(np.where(selected, thickness, 0.0),
                                    axis=(1, 2)) * area,
            }
        return result
