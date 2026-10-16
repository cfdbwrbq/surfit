#!/usr/bin/env python3
"""Runs Tcl scripts through the Python bindings and compares the results.

For every script this

  1. translates it line by line into calls on the `surfit` package (command
     names are the same in both front ends) and executes that in a scratch
     copy of the script's directory,
  2. runs the original through tclsh in another scratch copy,
  3. compares every data file both runs produced, byte for byte.

Scripts that need a command the bindings do not expose yet are reported as
SKIPPED together with the name of that command, so the coverage is explicit
rather than quietly incomplete.

Some directories are pipelines: 04_thickness_surface.tcl loads data files that
02_top_surface.tcl wrote, and 00_run_all.tcl sources them in order.  Pass
--sequential to run every script of a directory in order inside one shared
scratch directory, which is how those examples are meant to be used.

Environment:
  SURFIT_BIN  directory holding the built package (default: <repo>/../build-cpp/bin)

Usage:
  python3 run_tcl_suite.py                                  # examples/surfit/tests
  python3 run_tcl_suite.py --sequential <directory>         # pipelines, in order
  python3 run_tcl_suite.py path/to/script.tcl               # one script
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

# Handled by the runner itself rather than by the bindings.
TCL_BUILTINS = {"load", "set", "puts", "unset"}
# Plotting has no Python binding yet and does not affect the gridded result.
IGNORED = {"surf_plot", "dem_plot"}
# In the Tcl front end these are variables traced into core globals; here they
# have to be routed to the corresponding call.
TRACED_VARIABLES = {
    "map_name": "set_map_name",
    "tol": "set_tol",
}
# Backslash sequences Tcl substitutes inside "..." and in bare words.
ESCAPES = {
    "a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r",
    "t": "\t", "v": "\v", "\\": "\\", '"': '"', "$": "$",
    "{": "{", "}": "}",
}


class Missing(Exception):
    """Raised when a script needs something the bindings do not offer."""


def unescape(text):
    """Applies Tcl's backslash substitution.

    Without this `pnts_read ... "\\t"` would pass the two characters backslash
    and t instead of a tab, the columns would be misread, and the solve would
    quietly produce garbage instead of failing.
    """
    result = []
    index = 0
    while index < len(text):
        char = text[index]
        if char != "\\" or index + 1 >= len(text):
            result.append(char)
            index += 1
            continue
        nxt = text[index + 1]
        if nxt in ESCAPES:
            result.append(ESCAPES[nxt])
            index += 2
        elif nxt == "\n":
            result.append(" ")
            index += 2
        elif nxt == "x" and index + 3 < len(text):
            try:
                result.append(chr(int(text[index + 2:index + 4], 16)))
                index += 4
            except ValueError:
                result.append(char)
                index += 1
        else:
            result.append(char)
            index += 1
    return "".join(result)


def tokenize(line):
    """Splits a Tcl command line into tokens, honouring double quotes."""
    tokens = []
    current = []
    quoted = False
    for char in line:
        if char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    return [unescape(token) for token in tokens]


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


def call(command, args, warnings, line_number):
    """Calls one binding and records calls that selected nothing."""
    func = getattr(surfit, command, None)
    if func is None:
        raise Missing("no binding for %r at line %d" % (command, line_number))
    try:
        result = func(*args)
    except TypeError as error:
        raise Missing("bad call %s%r at line %d: %s"
                      % (command, tuple(args), line_number, error))
    if isinstance(result, list) and result and not any(result):
        warnings.append("line %d: %s%r matched nothing" % (line_number, command, tuple(args)))


def execute(script, variables, warnings, depth=0):
    """Executes one Tcl script through the bindings."""
    if depth > 10:
        raise Missing("source recursion too deep at %s" % script)

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
        if command in TCL_BUILTINS:
            if command == "set":
                name = tokens[1]
                text = substitute(tokens[2], variables)
                variables[name] = text
                setter = TRACED_VARIABLES.get(name)
                if setter is not None:
                    getattr(surfit, setter)(to_value(text))
            continue
        if command == "source":
            execute(os.path.join(os.getcwd(), tokens[1]), variables, warnings,
                    depth + 1)
            continue
        if command == "cd":
            os.chdir(tokens[1])
            continue

        args = [to_value(substitute(token, variables)) for token in tokens[1:]]
        call(command, args, warnings, number)


def copy_into(script, workdir):
    """Mirrors the script's own directory into an empty scratch directory."""
    source_dir = os.path.dirname(os.path.abspath(script))
    for name in os.listdir(source_dir):
        src = os.path.join(source_dir, name)
        dst = os.path.join(workdir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def link_libraries(workdir):
    for name in os.listdir(BIN):
        if name.endswith(".so"):
            os.symlink(os.path.join(BIN, name), os.path.join(workdir, name))


def data_files(directory):
    """Every produced data file, as a path relative to the scratch root."""
    found = []
    for root, _dirs, names in os.walk(directory):
        for name in names:
            if name.endswith(".dat"):
                found.append(os.path.relpath(os.path.join(root, name), directory))
    return sorted(found)


def execute_python(script, workdir):
    """Runs one script through the bindings inside an already prepared dir."""
    root = os.getcwd()
    os.chdir(workdir)
    # The core logs straight to file descriptor 1, so silence it there rather
    # than by replacing sys.stdout.
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved = os.dup(1)
    warnings = []
    try:
        os.dup2(devnull, 1)
        execute(script, {}, warnings)
    finally:
        os.dup2(saved, 1)
        os.close(saved)
        os.close(devnull)
        os.chdir(root)
    return warnings


def compare(tcl_dir, py_dir, note):
    """Compares what both front ends produced."""
    tcl_files = data_files(tcl_dir)
    py_files = data_files(py_dir)

    if tcl_files != py_files:
        return "DIFF", "different outputs: tcl=%s python=%s" % (
            tcl_files, py_files)
    if not tcl_files:
        return "EMPTY", "no data files produced"

    for filename in tcl_files:
        with open(os.path.join(tcl_dir, filename), "rb") as handle:
            expected = handle.read()
        with open(os.path.join(py_dir, filename), "rb") as handle:
            actual = handle.read()
        if expected != actual:
            return "DIFF", "%s differs (%d vs %d bytes)" % (
                filename, len(expected), len(actual))
    return "PASS", note


def check_group(scripts):
    """Runs a group of scripts in order, each front end in its own scratch dir."""
    env = dict(os.environ, LD_LIBRARY_PATH=BIN)
    with tempfile.TemporaryDirectory() as py_dir, \
            tempfile.TemporaryDirectory() as tcl_dir:
        copy_into(scripts[0], py_dir)
        copy_into(scripts[0], tcl_dir)
        link_libraries(tcl_dir)

        warnings = []
        for script in scripts:
            label = os.path.basename(script)
            try:
                warnings.extend(execute_python(script, py_dir))
            except Missing as error:
                return "SKIP", "%s: %s" % (label, error)
            except Exception as error:  # noqa: BLE001 - report anything raised
                return "ERROR", "%s: %s: %s" % (label, type(error).__name__, error)
            try:
                subprocess.run(["tclsh", script], cwd=tcl_dir, env=env,
                               check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as error:
                return "TCL-FAIL", "%s: tclsh exited %d" % (label, error.returncode)

        note = "%d file(s)" % len(data_files(py_dir))
        if len(scripts) > 1:
            note += " from %d scripts" % len(scripts)
        if warnings:
            note += "; WARN " + warnings[0]
        return compare(tcl_dir, py_dir, note)


def collect(argv):
    if not argv:
        return sorted(os.path.join(TESTS, name)
                      for name in os.listdir(TESTS) if name.endswith(".tcl"))

    scripts = []
    for argument in argv:
        # Absolute, because execution happens after a chdir into a scratch copy.
        argument = os.path.abspath(argument)
        if os.path.isdir(argument):
            for root, _dirs, names in os.walk(argument):
                scripts.extend(os.path.join(root, name) for name in names
                               if name.endswith(".tcl"))
        elif os.path.exists(argument):
            scripts.append(argument)
        else:
            scripts.append(os.path.join(TESTS, "%s.tcl" % os.path.basename(argument)))
    return sorted(scripts)


def group_by_directory(scripts):
    groups = {}
    for script in scripts:
        groups.setdefault(os.path.dirname(script), []).append(script)
    return [groups[key] for key in sorted(groups)]


def main(argv):
    sequential = "--sequential" in argv
    scripts = collect([item for item in argv if item != "--sequential"])
    groups = group_by_directory(scripts) if sequential else [[s] for s in scripts]

    counts = {}
    for group in groups:
        status, note = check_group(group)
        counts[status] = counts.get(status, 0) + 1
        label = os.path.basename(group[0])[:-4]
        if len(group) > 1:
            label = "%s/ (%d)" % (os.path.basename(os.path.dirname(group[0])),
                                  len(group))
        print("%-9s %-34s %s" % (status, label, note))

    print()
    print("TOTAL %d: %s" % (len(groups), "  ".join(
        "%s=%d" % (key, counts[key]) for key in sorted(counts))))

    if counts.get("DIFF") or counts.get("ERROR") or counts.get("TCL-FAIL"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
