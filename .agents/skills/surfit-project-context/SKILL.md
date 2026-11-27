---
name: surfit-project-context
description: >
  Use before any surfit task involving product direction, the workbench, docs,
  marketing, repository hygiene or release. Captures the user's standing
  decisions and boundaries so those decisions do not need to be restated.
---

# surfit project context

This is the short version of decisions already made in the project. Read it
before proposing a direction, changing the repository layout, writing public
copy or preparing a release.

## Standing decisions

- **Audience:** geologist, geophysicist, reservoir/development geologist and GIS
  specialist. Developers are integration users, not the marketing audience.
- **Two interfaces, one engine:** a human uses `workbench/`; an agent uses the
  Python API and the `surfit` CLI. Do not market workbench as an AI feature or
  as a wheel dependency.
- **Core is frozen** unless the user explicitly asks for engine work. Workbench,
  wrappers, docs and release tooling come first.
- **One repository:** workbench lives in `surfit/workbench`; do not split it
  into another repository or revive the obsolete `python` branch. The 2015
  prototype is archived as tag `archive/python-2015`; current Python code is on
  `master`.
- **Canonical checkout:** the surfit repository root; workbench is its
  `workbench/` directory. The sibling `surfit-studio/` is an obsolete local
  copy. Never start it by mistake.
- **Language:** answer the user in Russian. Public READMEs are maintained in
  English, Russian and Chinese. Code identifiers, comments and workbench UI are
  English.
- **Repository content is the result, not the process:** do not track plans,
  audits, cleanup reports, review notes, generated screenshots or build output.
  `.agents/skills/` is the exception: these are the agent-facing product
  instructions and are tracked.
- **No overclaiming:** WPS runs a configured policy with per-file exceptions;
  it is not 100% WPS compliance and must not carry a badge implying that.
- **Release only when requested.** `v3.7.5` is the current release. A published
  tag is immutable; a later correction goes on `master` and, if needed, into a
  new patch release.

## Workbench conventions

- The workbench is a local single-user app: FastAPI + vanilla ES modules +
  vendored three.js. No database, auth, PostGIS or map server.
- Auto behaviour must be explicit: an auto-mode checkbox fills and locks the
  dependent field; manual values survive unchecking.
- `?` help belongs next to the label text, never on a line under the input.
- Progress must be honest: stage changes and elapsed time are fine; do not fake
  a smooth percentage through the C++ solve.
- The workbench server must be restarted after backend changes; static frontend
  changes only need a page reload.
- Browser tests use the workbench `tests/browser_*.js` scripts; screenshots are
  local output and stay ignored.

## Release boundaries

Use `.agents/skills/release-sync/SKILL.md` before preparing or checking a
release. The non-negotiable sequence is: version files -> full gate -> wheels
-> docs archive -> tag -> GitHub release -> post-release workflow pin.

If a request conflicts with these decisions, say so once and ask for the
specific override; do not silently reintroduce an old plan.
