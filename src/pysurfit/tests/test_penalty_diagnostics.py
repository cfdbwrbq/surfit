"""Penalty loops expose residual history and iteration counts."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    task = surfit.Session(map_name="penalty-report", tol=1e-6)
    assert all(task.read_points(
        os.path.join(REPO, "examples", "surfit", "tests", "data",
                     "7points.txt"), "7points"))
    task.grid_auto()
    task.leq(120)
    task.geq(80)
    task.points("7points")
    task.completer()
    task.solve()
    report = task.rule_report()
    task.close()
    conditions = [rule for rule in report["rules"]
                  if rule["residual"] is not None]
    assert conditions
    assert any(rule["penalty_iterations"] > 0 for rule in conditions)
    assert any(len(rule["residual_history"]) > 0 for rule in conditions)
    assert all(rule["residual"] >= 0 for rule in conditions)
    print("PASS: penalty residual history and iterations")


if __name__ == "__main__":
    main()
