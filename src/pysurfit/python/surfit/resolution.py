"""Resolution and support diagnostics.

This is a support-based first slice, not a point-spread-function inversion.
It answers the practical questions: how many samples per cell, what fraction
of the grid is covered, what data spacing the grid claims to resolve, and
whether the grid is finer than the samples can support.
"""

import numpy as np


def _extent(extent):
    required = ("min_x", "max_x", "min_y", "max_y", "step_x", "step_y",
                "count_x", "count_y")
    missing = [name for name in required if name not in extent]
    if missing:
        raise ValueError("extent is missing: %s" % ", ".join(missing))
    return extent


def resolution_report(extent, x=None, y=None, values=None):
    """Return a JSON-ready support/resolution summary.

    ``nyquist`` is ``2 * max(step)``, the shortest feature the grid can carry.
    ``data_spacing`` is the square root of area per sample, a coarse estimate
    of the mean sample spacing.  A warning is reported when the grid step is
    less than a quarter of that spacing; the cells are then mostly
    interpolation, not information.
    """
    extent = _extent(extent)
    step_x = float(extent["step_x"])
    step_y = float(extent["step_y"])
    count_x = int(extent["count_x"])
    count_y = int(extent["count_y"])
    report = {
        "step_x": step_x,
        "step_y": step_y,
        "count_x": count_x,
        "count_y": count_y,
        "nyquist": 2.0 * max(step_x, step_y),
        "cells": count_x * count_y,
    }
    if values is not None:
        defined = np.isfinite(np.asarray(values, dtype=float))
        report["defined_fraction"] = float(defined.mean())
    if x is not None and y is not None:
        x = np.asarray(x, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
        if x.size != y.size:
            raise ValueError("x and y must have the same length")
        area = max((extent["max_x"] - extent["min_x"])
                   * (extent["max_y"] - extent["min_y"]), 1e-12)
        spacing = float(np.sqrt(area / max(x.size, 1)))
        report["samples"] = int(x.size)
        report["samples_per_cell"] = float(x.size) / max(report["cells"], 1)
        report["data_spacing"] = spacing
        if step_x < spacing / 4.0 or step_y < spacing / 4.0:
            report["warning"] = (
                "grid step is finer than the sample support; treat sub-cell "
                "detail as interpolation")
    return report
