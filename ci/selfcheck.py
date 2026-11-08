#!/usr/bin/env python3
"""Fast project self-check for skills, docs and the public Python surface.

Run it before a release or after changing agent-facing material:

    python3 ci/selfcheck.py

It does not replace ci/check.sh --full; it catches broken skill links, bad
frontmatter, a missing docs tree and a wheel/API that is not importable.
"""

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".agents" / "skills"
DOCS_CHECK = ROOT / "docs" / "check_docs.py"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def skill_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("%s: missing YAML frontmatter" % path)
    body = text.split("---", 2)[1]
    values = {}
    for line in body.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return text, values


def check_skills():
    errors = []
    names = {}
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        try:
            text, values = skill_frontmatter(path)
        except ValueError as error:
            errors.append(str(error))
            continue
        name = values.get("name", "")
        if name != path.parent.name:
            errors.append("%s: name %r does not match directory" % (path, name))
        if not values.get("description"):
            errors.append("%s: empty description" % path)
        if name in names:
            errors.append("%s: duplicate name %r" % (path, name))
        names[name] = path
        for target in LINK_RE.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append("%s: broken link %s" % (path, target))
    if errors:
        return errors
    print("skills: %d valid, links present" % len(names))
    return []


def check_docs():
    if not DOCS_CHECK.exists():
        return ["docs/check_docs.py is missing"]
    result = subprocess.run([sys.executable, str(DOCS_CHECK)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return ["docs/check_docs.py failed:\n" + result.stdout + result.stderr]
    print(result.stdout.strip())
    return []


def check_api():
    binary = os.environ.get("SURFIT_BIN")
    if not binary or not Path(binary).is_dir():
        print("api: SKIP (SURFIT_BIN is not a directory)")
        return []
    sys.path.insert(0, binary)
    try:
        module = importlib.import_module("surfit")
        importlib.import_module("surfit.tiled")
    except Exception as error:  # noqa: BLE001 - report the exact import failure
        return ["cannot import surfit from %s: %s" % (binary, error)]
    required = (
        "Session", "serial_threads", "area_read", "get_threads", "init_threads",
        "read_postgis", "diagnostics", "tiled",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        return ["surfit is missing: %s" % ", ".join(missing)]
    print("api: %s" % module.__file__)
    return []


def main():
    errors = []
    errors.extend(check_skills())
    errors.extend(check_docs())
    errors.extend(check_api())
    if errors:
        for error in errors:
            print("FAIL: %s" % error)
        return 1
    print("all selfchecks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
