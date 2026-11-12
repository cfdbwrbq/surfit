---
name: release-sync
description: >
  Use before publishing a surfit release, or when checking whether the published
  release, the git tag, CAPABILITIES, README, docs, skills and version files are
  in sync. Produces a concrete drift list and the patch-release rule; does not
  publish by itself.
---

# Release synchronization

A release is not just a green test suite.  The same facts live in several
places, and a tag freezes them.  This skill is the pre-release and post-release
drift check.  Publishing still requires an explicit user request.

## Invariants

1. **Version.** These four agree:
   - `pyproject.toml` (`[project].version`)
   - `src/CMakeLists.txt` (`set(VERSION ...)`)
   - `docs/conf.py` (`version`, `release`)
   - `src/pysurfit/python/surfit/_viewer.py`
2. **Public description.** `README.md`, `CAPABILITIES.md`, `.agents/skills/surfit/SKILL.md`,
   `docs/en/` and `docs/ru/` describe the same feature set.
3. **No contradiction.** Search for claims that a shipped feature is absent, or
   that an absent feature is shipped (for example `mesh/CAD export`,
   `rotated rasters are rejected`, `post-solve projection` for slope/curvature).
4. **AGENTS.md is not published.** It is local, ignored, and absent from the tag.
   Local agent instructions may change without a release.
5. **Optional dependencies are declared.** Every optional import used by a
   documented entry point has a matching `[project.optional-dependencies]`
   extra, or the docs say it is not installed by the wheel.
6. **Release candidate.** HEAD is the commit to tag; the working tree is clean;
   `check-release.sh` passes for that version; assets exist for every supported
   CPython version, plus docs zip and checksums.
7. **Published tag is immutable.** If drift is found after the tag, bump the
   patch version and release again; never move or delete the published tag.

## Pre-release check

Run from the repository root:

```bash
git status --porcelain
git log --oneline -5
git rev-parse --short HEAD
git ls-remote --heads fork master
git ls-remote --tags fork vX.Y.Z

grep -RIn --exclude-dir=.git --exclude-dir=build-ci \
  -E 'rotated rasters are rejected|no mesh/CAD export|post-solve projection|not residual per rule' \
  README.md CAPABILITIES.md .agents/skills docs/en docs/ru

python3 ci/selfcheck.py
python3 docs/check_docs.py
ci/check.sh --full
check-release.sh
```

Then inspect the actual release, not only the files:

```bash
gh -R cfdbwrbq/surfit release view vX.Y.Z \
  --json tagName,isDraft,isPrerelease,assets,url
gh -R cfdbwrbq/surfit run list --limit 4 \
  --json databaseId,name,headSha,headBranch,status,conclusion,url
```

`check-release.sh` must compare the tag commit with the checked-out HEAD.  A
pass on a different commit is not a pass.

## Drift list format

Report each item as `surface -> expected -> actual`.  Examples:

```text
CAPABILITIES.md -> mesh export present -> says "no mesh/CAD export"
v3.7.2 tag -> CAPABILITIES.md fixed -> tag still has old line
master -> pushed -> remote is one commit behind
```

Do not hide a known mismatch behind "docs are mostly updated".

## Post-release drift

If the only problem is documentation in a published tag:

1. fix it on `master`;
2. commit and push;
3. do **not** move the tag;
4. decide with the user whether a patch release is worth it.

A single Markdown correction does not automatically justify a release; a
source-archive inconsistency does.  State which one it is.

## Definition of synchronized

- local HEAD == the intended tag commit;
- remote branch and tag point to that commit;
- version files agree with the tag;
- README/CAPABILITIES/docs/skills agree with the shipped behaviour;
- `AGENTS.md` is not tracked;
- full suite and `check-release.sh` passed on that commit;
- release assets and CI match that commit;
- every known limitation is recorded in the docs, not only in chat.
