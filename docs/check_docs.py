#!/usr/bin/env python3
"""Checks that the two documentation trees are in step.

The English and Russian trees are maintained separately, which is simpler than
gettext catalogues but can drift.  A silently untranslated string is exactly the
kind of quiet failure worth a check, so this compares

  * the set of pages: every .rst in one tree must exist in the other,
  * the section structure: the same sequence of adornment characters,
  * the toctrees: the same entries in the same order.

Usage: python3 docs/check_docs.py
Exit status is 1 when the trees differ.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADORNMENT = re.compile(r"^([=\-~^\"'`#*+])\1*\s*$")
TOCTREE_ENTRY = re.compile(r"^\s{3,}(\S+)\s*$")


def pages(tree):
    found = []
    for root, _dirs, names in os.walk(os.path.join(HERE, tree)):
        for name in names:
            if name.endswith(".rst"):
                path = os.path.join(root, name)
                found.append(os.path.relpath(path, os.path.join(HERE, tree)))
    return sorted(found)


def structure(path):
    """Section adornment characters, in order, and toctree entries."""
    sections = []
    entries = []
    in_toctree = False
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip().startswith(".. toctree::"):
                in_toctree = True
                continue
            if in_toctree:
                if not line.strip():
                    continue
                if line.startswith(" "):
                    match = TOCTREE_ENTRY.match(line)
                    if match and not match.group(1).startswith(":"):
                        entries.append(match.group(1))
                    continue
                in_toctree = False
            if ADORNMENT.match(line):
                sections.append(line[0])
    return "".join(sections), entries


def main():
    english, russian = pages("en"), pages("ru")
    problems = []

    if english != russian:
        only_en = sorted(set(english) - set(russian))
        only_ru = sorted(set(russian) - set(english))
        if only_en:
            problems.append("only in en: %s" % ", ".join(only_en))
        if only_ru:
            problems.append("only in ru: %s" % ", ".join(only_ru))

    for name in sorted(set(english) & set(russian)):
        en_sections, en_entries = structure(os.path.join(HERE, "en", name))
        ru_sections, ru_entries = structure(os.path.join(HERE, "ru", name))
        if en_sections != ru_sections:
            problems.append("%s: section structure differs (%r vs %r)"
                            % (name, en_sections, ru_sections))
        if en_entries != ru_entries:
            problems.append("%s: toctree differs (%r vs %r)"
                            % (name, en_entries, ru_entries))

    # The command reference is generated from the interface files and headers;
    # a source change without a regeneration is exactly the kind of quiet drift
    # this check is for.
    generator = os.path.join(HERE, "make_command_reference.py")
    result = subprocess.run([sys.executable, generator, "--check"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        problems.append("commands.rst is stale: run %s" % generator)

    for line in problems:
        print("FAIL " + line)

    if problems:
        return 1
    print("OK   %d pages, both trees in step" % len(english))
    return 0


if __name__ == "__main__":
    sys.exit(main())
