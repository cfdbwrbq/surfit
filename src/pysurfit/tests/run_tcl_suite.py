#!/usr/bin/env python3
"""Runs the Tcl regression scripts through the Python bindings.

For every examples/surfit/tests/*.tcl script this

  1. runs the original through tclsh to get the reference output,
  2. translates the script line by line into calls on the `surfit` package
     (the command names are the same in both front ends),
  3. compares every .dat file both runs produced, byte for byte.

Tests that use a command the bindings do not expose yet are reported as
SKIPPED with the name of the missing command, so the coverage is explicit
rather than silently incomplete.

Environment:
  SURFIT_BIN  directory holding the built package (default: <repo>/../build-cpp/bin)

Usage: python3 run_tcl_suite.py [test-name ...]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
BIN = os.environ.get("SURFIT_BIN", os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
TESTS = os.path.join(REPO, "examples", "surfit", "tests")

sys.path.insert(0, BIN)

import surfit  # noqa: E402

NUMBER = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")
INTEGER = re.compile(r"^[+-]?\d+$")

# Commands handled by the runner itself rather than by the bindings.
TCL_BUILTINS = {"load", "set", "puts", "unset", "expr", "if", "proc", "return"}
# Plotting has no Python binding yet and does not affect the gridded result.
IGNORED = {"surf_plot", "dem_plot"}
# In the Tcl front end these are variables traced into core globals; here they
# have to be routed to the corresponding call.
TRACED_VARIABLES = {
    "map_name": "set_map_name",
    "tol": "set_tol",
}


class Missing(Exception):
    """Raised when a script needs a command the bindings do not expose."""


def tokenize(line):
    """Splits a Tcl command line into tokens, honouring double quotes."""
    tokens = []
    current = []
    quoted = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
        index += 1
    if current:
        tokens.append("".join(current))
    return tokens


def substitute(token, variables):
    """Expands $name references, as Tcl does."""
    def replace(match):
        name = match.group(1)
        if name not in variables:
            raise Missing("undefined Tcl variable $%s" % name)
        return variables[name]
    return re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", replace, token)


def to_value(token):
    """Tcl has no types; pick the Python type the binding expects."""
    if NUMBER.match(token):
        return int(token) if INTEGER.match(token) else float(token)
    return token


def run_script(script):
    """Executes one Tcl script through the bindings."""
    variables = {}
    with open(script) as handle:
        lines = handle.readlines()

    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = tokenize(line)
        if not tokens:
            continue
        command = tokens[0]
        if command in IGNORED:
            continue
        if command == "set":
            name = tokens[1]
            text = substitute(tokens[2], variables)
            variables[name] = text
            setter = TRACED_VARIABLES.get(name)
            if setter is not None:
                getattr(surfit, setter)(to_value(text))
            continue
        if command == "puts":
            continue
        if command == "load":
            continue
        if command in TCL_BUILTINS:
            raise Missing("unsupported Tcl builtin %r at line %d"
                          % (command, number))

        func = getattr(surfit, command, None)
        if func is None:
            raise Missing("no binding for %r at line %d" % (command, number))
        args = [to_value(substitute(token, variables)) for token in tokens[1:]]
        try:
            func(*args)
        except TypeError as error:
            raise Missing("bad call %s%r at line %d: %s"
                          % (command, tuple(args), number, error))


def data_files(directory):
    return sorted(name for name in os.listdir(directory)
                  if name.endswith(".dat"))


def run_tcl(script, workdir):
    os.symlink(os.path.join(TESTS, "data"), os.path.join(workdir, "data"))
    for name in os.listdir(BIN):
        if name.endswith(".so"):
            os.symlink(os.path.join(BIN, name), os.path.join(workdir, name))
    env = dict(os.environ, LD_LIBRARY_PATH=BIN)
    subprocess.run(["tclsh", script], cwd=workdir, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return data_files(workdir)


def run_python(script, workdir):
    os.symlink(os.path.join(TESTS, "data"), os.path.join(workdir, "data"))
    cwd = os.getcwd()
    os.chdir(workdir)
    # The core logs straight to file descriptor 1, so silence it at that level
    # rather than by replacing sys.stdout.
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved = os.dup(1)
    try:
        os.dup2(devnull, 1)
        run_script(script)
    finally:
        os.dup2(saved, 1)
        os.close(saved)
        os.close(devnull)
        os.chdir(cwd)
    return data_files(workdir)


def check(script):
    name = os.path.basename(script)
    with tempfile.TemporaryDirectory() as tcl_dir, \
            tempfile.TemporaryDirectory() as py_dir:
        try:
            tcl_files = run_tcl(script, tcl_dir)
        except subprocess.CalledProcessError as error:
            return "TCL-FAIL", "tclsh exited %d" % error.returncode
        try:
            py_files = run_python(script, py_dir)
        except Missing as error:
            return "SKIP", str(error)
        except Exception as error:  # noqa: BLE001 - report anything the core raises
            return "ERROR", "%s: %s" % (type(error).__name__, error)

        if tcl_files != py_files:
            return "DIFF", "different outputs: tcl=%s python=%s" % (
                tcl_files, py_files)
        if not tcl_files:
            return "EMPTY", "no .dat files produced"

        for filename in tcl_files:
            with open(os.path.join(tcl_dir, filename), "rb") as handle:
                expected = handle.read()
            with open(os.path.join(py_dir, filename), "rb") as handle:
                actual = handle.read()
            if expected != actual:
                return "DIFF", "%s differs (%d vs %d bytes)" % (
                    filename, len(expected), len(actual))
        return "PASS", "%d file(s)" % len(tcl_files)


def main(argv):
    if argv:
        scripts = [os.path.join(TESTS, "%s.tcl" % name) for name in argv]
    else:
        scripts = sorted(os.path.join(TESTS, name)
                         for name in os.listdir(TESTS)
                         if name.endswith(".tcl"))

    counts = {}
    details = []
    for script in scripts:
        status, note = check(script)
        counts[status] = counts.get(status, 0) + 1
        details.append((status, os.path.basename(script)[:-4], note))
        print("%-9s %-22s %s" % (status, details[-1][1], note))

    print()
    print("TOTAL %d: %s" % (len(scripts), "  ".join(
        "%s=%d" % (key, counts[key]) for key in sorted(counts))))

    if counts.get("DIFF") or counts.get("ERROR") or counts.get("TCL-FAIL"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
