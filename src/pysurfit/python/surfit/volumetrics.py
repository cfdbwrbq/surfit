"""Deterministic volumes and honest ensemble percentiles.

A per-cell calibrated interval is not enough to make a P10/P50/P90 volume:
the errors are spatially correlated.  ``volume_between`` is deterministic;
``volume_ensemble`` computes percentiles from coherent realizations supplied
by the caller.  Do not sum per-cell interval bounds and call it a volume range.
"""

import numpy as np


def cell_area(extent):
    """Area of one grid cell."""
    return float(extent["step_x"]) * float(extent["step_y"])


def volume_between(upper, lower, extent, mask=None, contact=None):
    """Volume between two surfaces (or a surface and a contact level).

    Only cells where both values are finite and ``mask`` is true contribute.
    ``lower`` may be a scalar contact level.  Positive and negative thickness
    both contribute; the result is signed and is not clipped.
    """
    upper = np.asarray(upper, dtype=float)
    if contact is not None:
        if lower is not None:
            raise ValueError("pass lower or contact, not both")
        lower = float(contact)
    if lower is None:
        raise ValueError("pass lower or contact")
    lower = np.asarray(lower, dtype=float)
    if upper.shape != lower.shape:
        raise ValueError("upper and lower must have the same shape")
    valid = np.isfinite(upper) & np.isfinite(lower)
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != upper.shape:
            raise ValueError("mask shape must match the surfaces")
        valid &= mask
    thickness = upper - lower
    area = cell_area(extent)
    values = thickness[valid]
    if values.size == 0:
        return {"volume": 0.0, "cells": 0, "area": area,
                "mean_thickness": None, "min_thickness": None,
                "max_thickness": None}
    return {
        "volume": float(values.sum() * area),
        "cells": int(values.size),
        "area": area,
        "mean_thickness": float(values.mean()),
        "min_thickness": float(values.min()),
        "max_thickness": float(values.max()),
    }


def volume_percentiles(volumes, levels=(10, 50, 90)):
    """Percentiles of an ensemble of coherent volume realizations."""
    volumes = np.asarray(volumes, dtype=float).ravel()
    volumes = volumes[np.isfinite(volumes)]
    if volumes.size == 0:
        raise ValueError("at least one finite volume is required")
    levels = [float(level) for level in levels]
    if any(not 0.0 <= level <= 100.0 for level in levels):
        raise ValueError("levels must be between 0 and 100")
    result = {("p%g" % level): float(np.percentile(volumes, level))
              for level in levels}
    result["n"] = int(volumes.size)
    return result


def volume_ensemble(upper_fields, lower_fields, extent, mask=None,
                    contact=None, levels=(10, 50, 90)):
    """Volumes from coherent realizations, then P10/P50/P90.

    ``upper_fields`` and ``lower_fields`` are equal-length sequences of
    arrays (or one side may be a scalar contact level via ``contact``).
    The realizations must be coherent: the same draw is used for every cell.
    """
    upper_fields = list(upper_fields)
    if contact is not None:
        lower_fields = [contact] * len(upper_fields)
    else:
        lower_fields = list(lower_fields)
    if len(upper_fields) != len(lower_fields):
        raise ValueError("upper and lower ensembles must have equal length")
    volumes = []
    for upper, lower in zip(upper_fields, lower_fields):
        item = volume_between(upper, lower, extent, mask=mask)
        volumes.append(item["volume"])
    result = volume_percentiles(volumes, levels=levels)
    result["volumes"] = volumes
    return result


def stack_volume(stack, upper, lower=None, contact=None, mask=None):
    """Volume between two named stack layers, or to a contact level."""
    upper_values = stack.values(upper)
    if contact is not None:
        lower_values = None
    else:
        if lower is None:
            raise ValueError("pass lower layer or contact")
        lower_values = stack.values(lower)
    extent = stack.extent()
    return volume_between(upper_values, lower_values, extent,
                          mask=mask, contact=contact)
