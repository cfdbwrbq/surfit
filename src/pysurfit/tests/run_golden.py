#!/usr/bin/env python3
"""Run the generated Python traces and compare output hashes to 3.7.2.

This runner needs no tclsh and no SWIG.  The manifest stores only output hashes;
the large Tcl reference directories stay outside the repository.
"""

import hashlib
import json
import os
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


def _digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


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
            return False, "differ: %s" % ", ".join(sorted(bad))
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
