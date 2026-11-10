"""Grid collars and cropping.

A solve near the edge of the data has less support than an interior cell.  A
common remedy is to create a larger grid (a collar), solve on it, and crop the
result back to the area of interest.  These helpers expand an extent and crop
an array without changing the engine's rule model.
"""

import numpy as np


def _extent(extent):
    required = ("min_x", "max_x", "min_y", "max_y", "step_x", "step_y",
                "count_x", "count_y")
    missing = [name for name in required if name not in extent]
    if missing:
        raise ValueError("extent is missing: %s" % ", ".join(missing))
    return dict(extent)


def pad_extent(extent, margin=0.0, percent=0.0):
    """Expand an extent by a coordinate margin and/or a percentage of its span.

    The node spacing is preserved.  The returned ``max_x``/``max_y`` are
    adjusted to the last node that fits, so ``count_x`` and ``count_y`` are
    exact for the new extent.
    """
    result = _extent(extent)
    span_x = result["max_x"] - result["min_x"]
    span_y = result["max_y"] - result["min_y"]
    pad_x = float(margin) + span_x * float(percent) / 100.0
    pad_y = float(margin) + span_y * float(percent) / 100.0
    if pad_x < 0 or pad_y < 0:
        raise ValueError("padding must not be negative")
    result["min_x"] -= pad_x
    result["min_y"] -= pad_y
    result["max_x"] += pad_x
    result["max_y"] += pad_y
    count_x = int(round((result["max_x"] - result["min_x"])
                        / result["step_x"])) + 1
    count_y = int(round((result["max_y"] - result["min_y"])
                        / result["step_y"])) + 1
    result["count_x"] = count_x
    result["count_y"] = count_y
    result["max_x"] = result["min_x"] + (count_x - 1) * result["step_x"]
    result["max_y"] = result["min_y"] + (count_y - 1) * result["step_y"]
    return result


def crop_surface(values, extent, bounds):
    """Crop ``values`` to ``bounds`` and return ``(values, extent)``.

    ``bounds`` is a mapping with ``min_x/max_x/min_y/max_y``.  The bounds must
    fall on the source grid; the result keeps the same node spacing.
    """
    values = np.asarray(values, dtype=float)
    source = _extent(extent)
    if values.shape != (int(source["count_y"]), int(source["count_x"])):
        raise ValueError("values shape does not match extent")
    target = _extent(bounds)
    first_col = int(round((target["min_x"] - source["min_x"])
                          / source["step_x"]))
    last_col = int(round((target["max_x"] - source["min_x"])
                         / source["step_x"]))
    first_row = int(round((target["min_y"] - source["min_y"])
                          / source["step_y"]))
    last_row = int(round((target["max_y"] - source["min_y"])
                         / source["step_y"]))
    if (first_col < 0 or first_row < 0 or last_col >= source["count_x"]
            or last_row >= source["count_y"]):
        raise ValueError("crop bounds are outside the source extent")
    cropped = values[first_row:last_row + 1, first_col:last_col + 1]
    result = dict(source)
    result["min_x"] = source["min_x"] + first_col * source["step_x"]
    result["max_x"] = source["min_x"] + last_col * source["step_x"]
    result["min_y"] = source["min_y"] + first_row * source["step_y"]
    result["max_y"] = source["min_y"] + last_row * source["step_y"]
    result["count_x"] = last_col - first_col + 1
    result["count_y"] = last_row - first_row + 1
    return cropped, result
