"""Block bootstrap preserves whole spatial blocks.

The callback records the sampled indices; the test checks that every sample is
a union of complete blocks, not an i.i.d. draw.

  python3 test_block_bootstrap.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    labels = np.array([0, 0, 0, 1, 1, 2, 2, 2, 2])
    samples = []

    def build(sample):
        samples.append(np.asarray(sample))
        return np.zeros((2, 2), dtype=float)

    result = surfit.bootstrap_uncertainty(
        build, labels.size, replicates=6, seed=7, blocks=labels)
    assert result["sampling"] == "block"
    assert result["blocks"] == 3
    assert result["std"].shape == (2, 2)
    for sample in samples:
        present = np.unique(labels[sample])
        for block in present:
            members = np.flatnonzero(labels == block)
            assert np.all(np.isin(members, sample)), (
                "block %d was only partially sampled" % block)

    x = np.array([0.1, 0.2, 1.1, 1.2])
    y = np.array([0.1, 0.2, 0.1, 0.2])
    block_labels = surfit.block_labels(x, y, 1.0)
    assert block_labels.size == 4
    assert np.unique(block_labels).size == 2
    auto = surfit.bootstrap_uncertainty(
        build, 4, replicates=3, seed=1, block_size=1.0, x=x, y=y)
    assert auto["sampling"] == "block"
    assert auto["blocks"] == 2
    print("PASS: block bootstrap samples complete blocks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
