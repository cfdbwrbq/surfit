"""Checks the local Tcl-style matcher against Tcl itself.

The engine used to call Tcl_StringMatch(); the replacement must agree with it.
Cases travel to tclsh base64-encoded so that quoting cannot mask a difference,
and each result carries its index so the comparison cannot drift.

Patterns with an unterminated '[' are reported separately: Tcl's answer there
depends on the memory following the string, so there is nothing to agree with.

Environment:
  SURFIT_BIN  directory holding the built package
              (default: <repo>/../build-cpp/bin)

Usage: python3 check_stringmatch.py
"""
import base64
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402

PATTERNS = [
    "", "*", "?", "a", "ab", "abc",
    "a*", "*a", "*a*", "a*c", "a?c", "?", "??", "???", "????",
    "**a", "a**b", "*a*b*", "*", "***",
    "[abc]", "[a-c]", "[a-c]x", "[a-c]*", "*[a-c]*",
    "[]]", "[]a]", "[[]", "[a-]", "[-a]", "[a-c", "[", "]", "a[b", "[!a]", "[^a]",
    "a\\*b", "a\\?b", "a\\\\b", "\\*", "\\[", "\\\\", "\\a",
    "[0-9]", "[0-9][0-9]", "x[0-9]y", "x[0-9]*", "*[0-9]",
    "a[bc]d", "a[bc]?", "[A-Z]*", "*[A-Z]",
    "*a?", "?a*", "*?*", "?*", "*?", "[*]", "[?]", "[*]a",
    "[\\]]", "[a\\-c]", "[\\\\]", "[a-c-e]", "[--0]", "[0-9a-f]",
    "[0-9a-fA-F]", "[^]a]", "[!]a]", "a[b-c]d", "[[a]", "[]", "[[]]",
    "[a-c][0-9]", "*[a-c]*[0-9]", "[-]", "[!]", "a[]b]",
]

STRINGS = [
    "", "a", "b", "c", "ab", "abc", "abcd", "a*c", "a?c", "ac", "abd", "axc",
    "x0y", "x5y", "42", "7", "aXd", "ABC", "abc123",
    "[", "]", "[]", "a[b", "a]b", "-", "a-b", "*", "?", "**", "a**b",
    "карта", "café", "top_D5", "map_area", "zones", "1016.ctr0",
    "\\", "a-c", "f", "F", "0", "9", "af", "a[]b", "[[a]]",
]


def balanced(pattern):
    """True when every '[' in the pattern is closed.

    Tcl does not define what an unterminated set means: it scans past the end of
    the pattern until it happens to find a ']', so the answer depends on the
    memory after the string.  Measured: `string match {a[b} {ab}` returns 1 on
    its own and 0 once another string has been decoded after it.  Those cases
    are reported separately instead of being compared.
    """
    in_set = False
    for char in pattern:
        if char == "[":
            in_set = True
        elif char == "]" and in_set:
            in_set = False
    return not in_set


def main():
    cases = [(p, s) for p in PATTERNS for s in STRINGS]

    with tempfile.TemporaryDirectory() as directory:
        cases_path = os.path.join(directory, "cases.txt")
        with open(cases_path, "w") as handle:
            for pattern, subject in cases:
                handle.write("%s\t%s\n" % (
                    base64.b64encode(pattern.encode()).decode(),
                    base64.b64encode(subject.encode()).decode()))

        tcl_script = os.path.join(directory, "match.tcl")
        with open(tcl_script, "w") as handle:
            handle.write(
                'set f [open [lindex $argv 0] r]\n'
                'set i 0\n'
                'while {[gets $f line] >= 0} {\n'
                '    lassign [split $line "\\t"] p s\n'
                '    set pattern [binary decode base64 $p]\n'
                '    set subject [binary decode base64 $s]\n'
                '    puts "$i [string match $pattern $subject]"\n'
                '    incr i\n'
                '}\n'
                'close $f\n')

        output = subprocess.run(
            ["tclsh", tcl_script, cases_path],
            capture_output=True, check=True).stdout.decode().split()

    # Each line carries its index, so a desynchronised comparison is impossible.
    expected = [None] * len(cases)
    for position in range(0, len(output), 2):
        expected[int(output[position])] = output[position + 1] == "1"
    assert all(item is not None for item in expected), "missing tcl results"

    mismatches = []
    skipped = 0
    for (pattern, subject), want in zip(cases, expected):
        if not balanced(pattern):
            skipped += 1
            continue
        got = surfit.string_match(pattern, subject)
        if got != want:
            mismatches.append((pattern, subject, want, got))

    print("cases: %d, compared: %d, skipped (unterminated set, undefined in Tcl): %d"
          % (len(cases), len(cases) - skipped, skipped))
    print("mismatches: %d" % len(mismatches))
    for pattern, subject, want, got in mismatches[:25]:
        print("  pattern=%r string=%r  tcl=%s local=%s"
              % (pattern, subject, want, got))
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
