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
END_OF_TOCTREE = ""


def pages(tree):
    """Every .rst page under one language tree, as relative paths."""
    found = []
    root_dir = os.path.join(HERE, tree)
    for root, _dirs, names in os.walk(root_dir):
        for name in names:
            if name.endswith(".rst"):
                path = os.path.join(root, name)
                found.append(os.path.relpath(path, root_dir))
    return sorted(found)


def _toctree_entry(line):
    """A toctree entry, None for a line to skip, or the end sentinel."""
    if not line.strip():
        return None
    if not line.startswith(" "):
        return END_OF_TOCTREE
    match = TOCTREE_ENTRY.match(line)
    if match and not match.group(1).startswith(":"):
        return match.group(1)
    return None


def _structure_lines(lines):
    """Section adornment characters and toctree entries, in order."""
    sections = []
    entries = []
    in_toctree = False
    for line in lines:
        if line.strip().startswith(".. toctree::"):
            in_toctree = True
            continue
        if in_toctree:
            entry = _toctree_entry(line)
            if entry is None:
                continue
            if entry == END_OF_TOCTREE:
                in_toctree = False
            else:
                entries.append(entry)
            continue
        if ADORNMENT.match(line):
            sections.append(line[0])
    return "".join(sections), entries


def structure(path):
    """Section adornment characters, in order, and toctree entries."""
    with open(path, encoding="utf-8") as source_file:
        lines = source_file.readlines()
    return _structure_lines(lines)


def _page_problems(english, russian):
    """Problems with the set of pages, if any."""
    problems = []
    only_en = sorted(set(english) - set(russian))
    only_ru = sorted(set(russian) - set(english))
    if only_en:
        problems.append("only in en: %s" % ", ".join(only_en))
    if only_ru:
        problems.append("only in ru: %s" % ", ".join(only_ru))
    return problems


def _compare_page(name):
    """Section and toctree differences for one page."""
    en_sections, en_entries = structure(os.path.join(HERE, "en", name))
    ru_sections, ru_entries = structure(os.path.join(HERE, "ru", name))
    problems = []
    if en_sections != ru_sections:
        problems.append("%s: section structure differs (%r vs %r)"
                        % (name, en_sections, ru_sections))
    if en_entries != ru_entries:
        problems.append("%s: toctree differs (%r vs %r)"
                        % (name, en_entries, ru_entries))
    return problems


def _structure_problems(english, russian):
    """Section and toctree differences for every common page."""
    problems = []
    for name in sorted(set(english) & set(russian)):
        problems.extend(_compare_page(name))
    return problems


def _command_problems():
    """The generated command reference must be current."""
    generator = os.path.join(HERE, "make_command_reference.py")
    check_result = subprocess.run(
        [sys.executable, generator, "--check"],
        capture_output=True,
        text=True,
    )
    if check_result.returncode != 0:
        return ["commands.rst is stale: run %s" % generator]
    return []


def _report(problems, page_count):
    """Prints the report and returns the process status."""
    for line in problems:
        sys.stdout.write("FAIL %s\n" % line)
    if problems:
        return 1
    sys.stdout.write("OK   %d pages, both trees in step\n" % page_count)
    return 0


def main():
    english, russian = pages("en"), pages("ru")
    problems = _page_problems(english, russian)
    problems.extend(_structure_problems(english, russian))
    problems.extend(_command_problems())
    return _report(problems, len(english))


if __name__ == "__main__":
    sys.exit(main())
