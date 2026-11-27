"""Portable numeric signatures used by the realworld golden gate."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_golden as golden


def main():
    with tempfile.TemporaryDirectory() as directory:
        text = os.path.join(directory, "values.txt")
        with open(text, "w", encoding="utf-8") as stream:
            stream.write("1 2 3\n4 5\n")
        signature = golden._numeric_signature(text)
        assert signature["defined"] == 5
        assert signature["min"] == 1.0
        assert signature["max"] == 5.0
        assert golden._numeric_matches(signature, signature)

        changed = dict(signature, mean=signature["mean"] + 1.0)
        assert not golden._numeric_matches(signature, changed)

        grid = os.path.join(directory, "grid.grd")
        with open(grid, "w", encoding="utf-8") as stream:
            stream.write("DSAA\n2 2\n0 1\n0 1\n1 4\n1 2 3 4\n")
        grid_signature = golden._numeric_signature(grid)
        assert grid_signature["shape"] == [2, 2]
        assert grid_signature["mean"] == 2.5
        assert golden._numeric_matches(grid_signature, grid_signature)
    print("PASS: golden numeric signatures")


if __name__ == "__main__":
    main()
