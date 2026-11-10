"""Reproducible provenance for a result or a quality report.

The engine formats do not carry units, CRS or the solver parameters, so these
fields are recorded next to the grid instead of being inferred from a file
name.  This is not a substitute for a full ISO 19115 record; it is the small,
machine-readable subset a headless run can always produce.
"""

import hashlib
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata as _metadata

import numpy as np

_CHUNK = 1024 * 1024


def engine_version():
    """Return the installed surfit version, or ``"unknown"`` in a source tree."""
    try:
        return _metadata.version("surfit")
    except _metadata.PackageNotFoundError:
        return "unknown"


def file_sha256(path):
    """SHA-256 of a file, read in chunks so large inputs do not fill RAM."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes(sources):
    """Return ``{path: sha256}`` for a path or a path -> hash mapping.

    A mapping is useful when the caller already hashed the inputs; otherwise
    every file is read and hashed here.  Paths are kept as given, so callers
    can record a relative name rather than a personal absolute path.
    """
    if sources is None:
        return {}
    items = sources.items() if hasattr(sources, "items") else (
        (path, None) for path in sources)
    hashes = {}
    for path, digest in items:
        key = str(path)
        hashes[key] = digest if digest is not None else file_sha256(path)
    return hashes


def build_provenance(task, sources=None):
    """Fields shared by ``report()`` and the JSON metadata sidecar."""
    task_metadata = getattr(task, "metadata", {})
    crs = task_metadata.get("crs")
    units = task_metadata.get("z_units") or task_metadata.get("units")
    return {
        "engine": "surfit",
        "engine_version": engine_version(),
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "map_name": getattr(task, "_map_name", None),
        "crs": crs,
        "grid_mapping": task_metadata.get("grid_mapping") or crs,
        "units": units,
        "sources": source_hashes(sources),
    }
