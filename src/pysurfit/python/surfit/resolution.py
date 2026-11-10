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


def psf_report(values, extent, center=None, threshold=0.5):
    """Measure the width of an impulse response on a regular grid.

    ``values`` is the solved response to a single impulse (or any isolated
    feature).  The peak is the largest absolute value; ``center`` may name its
    ``(x, y)`` if the peak is not the intended feature.  ``half_width`` is the
    radial distance where the response falls to ``threshold`` of the peak;
    ``sigma`` is a Gaussian fit inside that radius.  This is a measurement on
    a field you supply, not a covariance model.
    """
    values = np.asarray(values, dtype=float)
    extent = _extent(extent)
    if values.shape != (int(extent["count_y"]), int(extent["count_x"])):
        raise ValueError("values shape does not match extent")
    amplitude = np.abs(values)
    if center is None:
        row, column = np.unravel_index(int(np.nanargmax(amplitude)),
                                       amplitude.shape)
    else:
        column = int(round((float(center[0]) - extent["min_x"])
                           / extent["step_x"]))
        row = int(round((float(center[1]) - extent["min_y"])
                        / extent["step_y"]))
        column = min(max(column, 0), values.shape[1] - 1)
        row = min(max(row, 0), values.shape[0] - 1)
    peak = float(amplitude[row, column])
    if not np.isfinite(peak) or peak <= 0:
        raise ValueError("the impulse response has no positive peak")
    xs = extent["min_x"] + np.arange(values.shape[1]) * extent["step_x"]
    ys = extent["min_y"] + np.arange(values.shape[0]) * extent["step_y"]
    grid_x, grid_y = np.meshgrid(xs, ys)
    distance = np.hypot(grid_x - xs[column], grid_y - ys[row])
    response = amplitude / peak
    order = np.argsort(distance.ravel())
    flat_distance = distance.ravel()[order]
    flat_response = response.ravel()[order]
    half = None
    for index in range(1, flat_distance.size):
        if flat_response[index] <= threshold:
            before = flat_response[index - 1]
            after = flat_response[index]
            fraction = ((before - threshold) / (before - after)
                        if before != after else 0.0)
            half = (flat_distance[index - 1]
                    + fraction * (flat_distance[index]
                                  - flat_distance[index - 1]))
            break
    if half is None:
        half = float(np.max(distance))
    inside = (flat_distance > 0) & (flat_distance <= half) & (
        flat_response > 0)
    sigma = float("nan")
    if np.count_nonzero(inside) >= 3:
        slope = np.polyfit(flat_distance[inside] ** 2,
                           np.log(flat_response[inside]), 1)[0]
        if slope < 0:
            sigma = float(np.sqrt(-1.0 / (2.0 * slope)))
    return {
        "peak": peak,
        "center": (float(xs[column]), float(ys[row])),
        "half_width": float(half),
        "sigma": sigma,
        "grid_step": max(float(extent["step_x"]), float(extent["step_y"])),
        "resolved_features": float(2.0 * half),
    }


def estimate_psf(build, x0, y0, extent, threshold=0.5):
    """Solve one impulse and measure its response.

    ``build(x0, y0)`` must return a solved task or an array of the same shape
    as the grid.  The callback owns the impulse construction; this function
    only measures.  Returns ``{"values": ..., "report": ...}``.
    """
    result = build(x0, y0)
    if hasattr(result, "values"):
        result = result.values()
    values = np.asarray(result, dtype=float)
    return {"values": values,
            "report": psf_report(values, extent, (x0, y0), threshold)}
