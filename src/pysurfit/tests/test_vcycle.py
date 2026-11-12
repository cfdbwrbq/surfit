"""Galerkin V-cycle prototype: residual must decrease on every cycle."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    result = surfit.poisson_vcycle(32, cycles=5)
    residuals = result["residuals"]
    assert len(residuals) == 5
    assert all(right < left for left, right in zip(residuals, residuals[1:]))
    assert residuals[-1] < residuals[0] * 0.2
    assert result["values"].shape == (32, 32)
    print("PASS: Galerkin V-cycle residual reduction")


if __name__ == "__main__":
    main()
