"""Benchmark layered stacks against a direct in-memory loop.

The numbers are wall-clock timings on the caller's data; this is a tool, not a
CI performance assertion.  ``direct`` solves each builder in a loop, while
``sequential`` and ``parallel`` use SurfaceStack.
"""

import statistics
import time

from surfit.stack import SurfaceStack


def _timed(function):
    started = time.perf_counter()
    function()
    return time.perf_counter() - started


def benchmark_stack(builders, repeats=3, workers=None):
    """Compare direct, sequential and parallel stack solves.

    ``builders`` is a mapping layer name -> callable returning a Session.
    Returns ``times`` in seconds and the median/mean per mode.  The builders
    are called repeatedly, so they must create fresh Sessions.
    """
    if not builders:
        raise ValueError("builders must not be empty")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    timings = {"direct": [], "sequential": [], "parallel": []}
    for _ in range(repeats):
        timings["direct"].append(_timed(
            lambda: [_direct(build) for build in builders.values()]))
        for mode in ("sequential", "parallel"):
            stack = SurfaceStack("benchmark")
            for name, build in builders.items():
                stack.add_layer(name, build)
            timings[mode].append(_timed(
                lambda stack=stack, mode=mode: stack.solve(
                    parallel=mode == "parallel", workers=workers)))
            stack.close()
    summary = {}
    for mode, values in timings.items():
        summary[mode] = {
            "seconds": values,
            "median": float(statistics.median(values)),
            "mean": float(statistics.mean(values)),
        }
    summary["speedup_parallel"] = (
        summary["sequential"]["median"] / summary["parallel"]["median"])
    return summary


def _direct(build):
    task = build()
    task.solve()
    close = getattr(task, "close", None)
    if close is not None:
        close()
    return task
