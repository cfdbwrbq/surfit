"""Solver benchmark helper returns timings for each requested method."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def build():
    task = surfit.Session(map_name="solver-bench", tol=1e-7)
    task.add_points([0, 1, 0, 1], [0, 0, 1, 1], [1, 2, 3, 4], name="p")
    task.grid(0, 1, 0.1, 0, 1, 0.1)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    result = surfit.benchmark_solvers(build, solvers=("cg", "jcg"))
    assert set(result) == {"cg", "jcg"}
    assert result["cg"]["median"] >= 0
    assert result["jcg"]["seconds"]
    print("PASS: solver benchmark helper")


if __name__ == "__main__":
    main()
