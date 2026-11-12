"""Optional xarray/Zarr export for SurfaceStack.

xarray and zarr are not dependencies.  The Dataset is eager; Dask-backed lazy
loading is deliberately not promised here.
"""

import numpy as np


def to_xarray(stack):
    """Return a Dataset with x/y coordinates, layers and intervals."""
    try:
        import xarray as xr
    except ImportError as error:
        raise ImportError("to_xarray needs xarray") from error
    extent = stack.extent()
    x = float(extent["min_x"]) + np.arange(
        int(extent["count_x"])) * float(extent["step_x"])
    y = float(extent["min_y"]) + np.arange(
        int(extent["count_y"])) * float(extent["step_y"])
    variables = {}
    for name in stack.layer_names():
        variables[name] = (("y", "x"), np.asarray(stack.values(name)))
        try:
            interval = stack.interval(name)
        except KeyError:
            continue
        variables[name + "_lower"] = (("y", "x"),
                                      np.asarray(interval["lower"]))
        variables[name + "_upper"] = (("y", "x"),
                                      np.asarray(interval["upper"]))
    dataset = xr.Dataset(variables, coords={"x": x, "y": y})
    dataset.attrs.update({
        "name": stack._name,
        "extent": dict(extent),
        "layer_order": ",".join(stack.layer_names()),
    })
    provenance = {name: stack.provenance(name)
                  for name in stack.layer_names()
                  if stack.provenance(name)}
    if provenance:
        dataset.attrs["provenance"] = provenance
    return dataset


def to_zarr(stack, path, mode="w", **kwargs):
    """Write the eager Dataset to Zarr; zarr and xarray are optional."""
    try:
        import zarr  # noqa: F401
    except ImportError as error:
        raise ImportError("to_zarr needs zarr") from error
    dataset = to_xarray(stack)
    dataset.to_zarr(path, mode=mode, **kwargs)
    return path
