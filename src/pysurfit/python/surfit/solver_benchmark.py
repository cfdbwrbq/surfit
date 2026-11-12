"""Measure the existing linear solvers on a caller-built task.

The benchmark is a decision tool, not a promise of a preconditioner.  It is
kept separate from the solver so experiments do not change production results.
"""

import statistics
import time


def benchmark_solvers(build, solvers=("cg", "jcg", "ssor", "jacobi", "rf"),
                      repeats=1):
    """Time fresh builds/solves for each solver name.

    ``build()`` must return a solved-capable Session with its grid and rules
    already configured.  The task is closed after each solve.
    """
    if repeats < 1:
        raise ValueError("repeats must be positive")
    results = {}
    for name in solvers:
        values = []
        for _ in range(repeats):
            task = build()
            task.set_solver(name)
            started = time.perf_counter()
            task.solve()
            values.append(time.perf_counter() - started)
            task.close()
        results[name] = {
            "seconds": values,
            "median": float(statistics.median(values)),
            "mean": float(statistics.mean(values)),
        }
    return results
