#!/bin/sh
#
# Builds surfit and runs every check, the way continuous integration does.
#
#   ci/check.sh            build, the 35 test scripts, the 47 Python examples,
#                          parity, the name matcher, the viewer, sessions, every
#                          command against Tcl, and a wheel that installs and
#                          solves on its own (about twenty minutes)
#   ci/check.sh --full     the same, plus the 29 realworld pipelines (an hour
#                          more), for the nightly run
#
# Everything happens in build-ci/, so a development build is left alone.
# Environment:
#   BUILD_DIR      where to build (default: <repo>/build-ci)
#   PYBIND11_DIR   pybind11's CMake directory, if find_package cannot see it
#   PYTHON         interpreter to use (default: python3)
#
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
BUILD=${BUILD_DIR:-$HERE/build-ci}
PYTHON=${PYTHON:-python3}
TESTS="$HERE/src/pysurfit/tests"

FULL=0
for argument in "$@"; do
    case $argument in
        --full) FULL=1 ;;
        *) echo "unknown argument: $argument" >&2; exit 2 ;;
    esac
done

FAILED=""

step() {
    printf '\n=== %s ===\n' "$1"
}

# Runs a command, records a failure and carries on, so one broken area does not
# hide the state of the others.
run() {
    name=$1
    shift
    if "$@"; then
        return 0
    fi
    echo "FAILED: $name" >&2
    FAILED="$FAILED $name"
    return 0
}

step "configure and build"
cmake_args="-S $HERE/src -B $BUILD -DCMAKE_BUILD_TYPE=Release -DSURFIT_BUILD_TCL=ON"
if [ -n "${PYBIND11_DIR:-}" ]; then
    cmake_args="$cmake_args -Dpybind11_DIR=$PYBIND11_DIR"
fi
# shellcheck disable=SC2086
cmake $cmake_args > /dev/null
cmake --build "$BUILD" -j "$(nproc 2>/dev/null || echo 2)" > /dev/null

SURFIT_BIN="$BUILD/bin"
export SURFIT_BIN

step "the 35 test scripts, Tcl and Python side by side"
run tests "$PYTHON" "$TESTS/run_tcl_suite.py"

step "every Python example, against its Tcl original"
run examples "$PYTHON" "$TESTS/test_examples.py"

step "parity and numpy round trip"
run parity "$PYTHON" "$TESTS/test_parity.py"

step "name matching against Tcl"
run string-match "$PYTHON" "$TESTS/check_stringmatch.py"

step "two tasks in one process"
run sessions "$PYTHON" "$TESTS/test_sessions.py"

step "the object and settings commands, against Tcl"
run commands "$PYTHON" "$TESTS/test_commands.py"

step "every command, against Tcl"
run all-commands "$PYTHON" "$TESTS/test_all_commands.py"

step "the viewer"
run viewer "$PYTHON" "$TESTS/test_viewer.py"

step "a wheel that installs and solves"
WHEEL_TARGET="$BUILD/wheel-install"
rm -rf "$HERE/dist" "$WHEEL_TARGET"
if "$PYTHON" -m pip wheel "$HERE" -w "$HERE/dist" --no-deps > "$BUILD/wheel.log" 2>&1; then
    if "$PYTHON" -m pip install --no-deps --target "$WHEEL_TARGET" \
            "$HERE"/dist/*.whl >> "$BUILD/wheel.log" 2>&1; then
        # No LD_LIBRARY_PATH: the wheel has to find its own libraries.
        if env -u LD_LIBRARY_PATH PYTHONPATH="$WHEEL_TARGET" \
                "$PYTHON" "$HERE/ci/wheel_smoke.py" "$WHEEL_TARGET"; then
            :
        else
            FAILED="$FAILED wheel-smoke"
        fi
    else
        echo "FAILED: wheel install" >&2
        FAILED="$FAILED wheel-install"
    fi
else
    echo "FAILED: wheel build" >&2
    FAILED="$FAILED wheel-build"
fi

if [ "$FULL" = "1" ]; then
    step "the 29 realworld pipelines, Tcl and Python side by side"
    run realworld "$PYTHON" "$TESTS/run_tcl_suite.py" --sequential \
        "$HERE/examples/surfit/realworld"
fi

printf '\n'
if [ -n "$FAILED" ]; then
    echo "FAILED:$FAILED"
    exit 1
fi
echo "all checks passed"
