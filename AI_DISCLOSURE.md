# AI-assisted development

This repository contains two kinds of work.

## The original engine

surfit was written by **M. V. Dmitrievsky** and **V. N. Kutrunov** between 2002
and 2015: the C++ engine, the Tcl front end, the file-format plugin and the
original examples. That code is human-authored and remains under its original
copyright and the GNU General Public License, version 2.

## The 2026 port

The Python port — pybind11 bindings, the test harness, the build and packaging
scripts, the Sphinx documentation and the text of this file — was produced with
an **AI coding agent under human direction and review**. The human maintainer
decided the scope, reviewed the changes, ran the tests and is responsible for
the result.

The port was checked against the original wherever possible:

- 49 Tcl examples are executed through the Python front end and the resulting
  data files are compared **byte for byte**;
- 504 command steps are run from both front ends;
- `ci/check.sh` runs the full suite, the documentation build and the wheel
  checks;
- the manylinux wheels are installed and exercised on CPython 3.9–3.13.

These checks reduce the risk of mistakes; they do not eliminate it. AI-assisted
code can still contain errors, and the software is provided under GPL-2
**without warranty**, like the original.

## What this does not mean

- It does not mean the original authors used AI or endorse this port. The
  port is not their work, and they are not responsible for it.
- It does not mean there is no human authorship in the port: the direction,
  review, acceptance and integration are human work. The AI is a tool, not a
  legal author.
- It does not change the licence. The repository is distributed under
  GPL-2.0-only; `src/surfit/src/triangle.cpp` (Shewchuk's Triangle) has its own
  terms, so review it before shipping binaries.

## AI usage in numbers

The measured sessions, requests and token counts are on the documentation
statistics page: [`docs/en/stats.rst`](docs/en/stats.rst) (and its Russian
counterpart), with the method used to collect them.

## If you find a problem

Open an issue with the version (release tag or commit), the command, the input
and what you expected. That is the fastest way to get it fixed and, if needed,
released.
