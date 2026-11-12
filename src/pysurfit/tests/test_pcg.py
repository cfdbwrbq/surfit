"""Prototype diagonal-preconditioned CG matches ordinary CG."""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def solve(name):
    task = surfit.Session(map_name="pcg", tol=1e-7)
    task.set_solver(name)
    task.add_points([0, 1, 0, 1], [0, 0, 1, 1], [1, 2, 3, 4], name="p")
    task.grid(0, 1, 0.1, 0, 1, 0.1)
    task.points("p")
    task.completer(1, 1.6)
    task.solve()
    values = task.values().copy()
    task.close()
    return values


def main():
    cg = solve("cg")
    pcg = solve("pcg")
    assert np.allclose(cg, pcg, rtol=1e-4, atol=1e-4)
    print("PASS: prototype pcg matches cg")


if __name__ == "__main__":
    main()
