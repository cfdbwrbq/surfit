#!/usr/bin/env python3
"""Run the generated Python traces and compare output hashes to 3.7.2.

This runner needs no tclsh and no SWIG.  The manifest stores only output hashes;
the large Tcl reference directories stay outside the repository.
"""

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
GOLDEN = os.path.join(HERE, "golden", "3.7.2")
MANIFEST = os.path.join(GOLDEN, "manifest.json")
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(ROOT), "build-cpp", "bin"))


_VERSION = re.compile(rb"surfit-[0-9]+\.[0-9]+\.[0-9]+")


def _normalize(data):
    """Ignore the release string in native .dat headers."""
    return _VERSION.sub(b"surfit-VERSION", data)


def _digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(_normalize(handle.read())).hexdigest()


def _numeric_signature(path):
    """Return a portable summary for native grid outputs, or None."""
    if path.endswith(".dat"):
        try:
            if BIN not in sys.path:
                sys.path.insert(0, BIN)
            import surfit
            task = surfit.Session(map_name="golden-compare", tol=1e-7)
            loaded = task.surf_load(path)
            if not any(loaded):
                return None
            values = task.values()
            defined = surfit.defined_mask(values)
            if not defined.any():
                return None
            data = values[defined]
            return {"kind": "grid", "shape": list(values.shape),
                    "defined": int(defined.sum()), "min": float(data.min()),
                    "max": float(data.max()), "mean": float(data.mean())}
        except Exception:
            return None
    if path.endswith(".txt"):
        try:
            with open(path, encoding="utf-8", errors="replace") as stream:
                numbers = [float(value) for value in stream.read().split()]
            if len(numbers) < 2:
                return None
            return {"kind": "numbers", "shape": [len(numbers)],
                    "defined": len(numbers), "min": min(numbers),
                    "max": max(numbers), "mean": sum(numbers) / len(numbers)}
        except (OSError, ValueError):
            return None
    if path.endswith(".grd"):
        try:
            with open(path, encoding="utf-8", errors="replace") as stream:
                lines = stream.read().splitlines()
            if not lines or lines[0].strip().upper() != "DSAA":
                return None
            nx, ny = [int(value) for value in lines[1].split()]
            numbers = [float(value) for value in " ".join(lines[5:]).split()]
            if len(numbers) < nx * ny:
                return None
            data = numbers[:nx * ny]
            return {"kind": "grid", "shape": [ny, nx], "defined": len(data),
                    "min": min(data), "max": max(data),
                    "mean": sum(data) / len(data)}
        except (OSError, ValueError, IndexError):
            return None
    return None


def _numeric_matches(want, got, rtol=None, atol=None):
    if not want or not got or want.get("kind") != got.get("kind"):
        return False
    if want.get("shape") != got.get("shape") or want.get("defined") != got.get("defined"):
        return False
    if rtol is None:
        rtol = 1e-3 if want["kind"] == "numbers" else 1e-4
    if atol is None:
        atol = 1e-3 if want["kind"] == "numbers" else 1e-6
    for key in ("min", "max", "mean"):
        if not math.isclose(float(want[key]), float(got[key]),
                            rel_tol=rtol, abs_tol=atol):
            return False
    return True


def _copy_source(source, directory):
    for name in os.listdir(source):
        src = os.path.join(source, name)
        dst = os.path.join(directory, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def _outputs(directory, source):
    found = {}
    for root, _dirs, names in os.walk(directory):
        for name in names:
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            if name.endswith((".so", ".dylib", ".dll", ".pyd")):
                continue
            if name == "surfit.log" or name.endswith(".ps"):
                continue
            relative = os.path.relpath(path, directory)
            original = os.path.join(source, relative)
            if os.path.isfile(original) and _digest(path) == _digest(original):
                continue
            found[relative] = _digest(path)
    return found


def run_case(case):
    source = os.path.join(ROOT, case["source"])
    trace = os.path.join(GOLDEN, case["trace"])
    with tempfile.TemporaryDirectory() as directory:
        _copy_source(source, directory)
        target = os.path.join(directory, "__trace__.py")
        shutil.copy2(trace, target)
        env = dict(os.environ, SURFIT_BIN=BIN,
                   PYTHONPATH=BIN + os.pathsep + os.environ.get("PYTHONPATH", ""))
        result = subprocess.run([sys.executable, target], cwd=directory,
                                env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        os.unlink(target)
        if result.returncode != 0:
            return False, "exit %d: %s" % (result.returncode,
                                           result.stderr.strip()[-300:])
        got = _outputs(directory, source)
        want = case["outputs"]
        if set(got) != set(want):
            return False, "outputs got %s want %s" % (sorted(got), sorted(want))
        bad = [name for name in want if got[name] != want[name]]
        if bad:
            numeric = case.get("numeric", {})
            signatures = {name: _numeric_signature(os.path.join(directory, name))
                          for name in bad}
            if all(name in numeric and
                   _numeric_matches(numeric[name], signatures[name])
                   for name in bad):
                return True, "%d file(s), numeric tolerance" % len(want)
            details = "; ".join("%s want=%s got=%s" %
                                (name, numeric.get(name), signatures[name])
                                for name in sorted(bad))
            return False, "differ: %s [%s]" % (", ".join(sorted(bad)), details)
        return True, "%d file(s)" % len(want)


def main():
    with open(MANIFEST, encoding="utf-8") as handle:
        manifest = json.load(handle)
    failed = 0
    for case in manifest["cases"]:
        ok, note = run_case(case)
        strict = case.get("strict", True)
        if ok:
            status = "PASS"
        elif strict:
            status = "FAIL"
            failed += 1
        else:
            status = "WARN"
            note += " (cross-platform binary output; not a gate)"
        print("%-9s %-28s %s" % (status, case["key"], note))
    print("TOTAL %d: %s" % (len(manifest["cases"]),
                            "PASS" if not failed else "FAIL"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
