---
name: surfit-workbench
description: >
  Use when changing or testing the surfit browser workbench: map, 3D result,
  grid rules, area/surface rules, auto cell/bounds, cross-section, fullscreen,
  progress, help, projects, FastAPI endpoints or Playwright checks.
---

# Working on the surfit workbench

Canonical location:

```text
<surfit>/workbench
```

Do **not** use the sibling `surfit-studio/`; that is the old standalone copy
and does not contain current features.

## Run

```bash
cd workbench
./bootstrap.sh            # once: installs Python deps into .site
./run.sh                  # finds ../build-ci/bin and serves :8000
```

For a test port:

```bash
PORT=8010 ./run.sh
```

Backend changes require restarting uvicorn. Frontend changes only require a
browser reload. Static files are served from `frontend/`.

## Architecture map

- `backend/app.py` — jobs, preview, schema, projects, SHP/GeoJSON parsing,
  area/global rule wiring, stage progress.
- `frontend/app.js` — uploads, preview, map canvas, three.js result, section,
  auto controls, help popovers, projects.
- `frontend/index.html` / `style.css` — layout and controls.
- `tests/test_app.py` — API/real-solve smoke test.
- `tests/browser_*.js` — Playwright UI checks. Screenshots go to ignored
  `tests/screenshots/`.

## Change checklist

When adding a new job/project setting, update all of these:

1. FastAPI form parameter in the relevant endpoint(s).
2. `_solve` call or background job payload.
3. Project `settings` dict in `save_project`.
4. Project load in `frontend/app.js`.
5. `projectBody()` in `frontend/app.js`.
6. A browser assertion that the setting survives save/load.

When changing preview-derived UI, update both branches of `schedulePreview()`:
the success path and the no-active-files path. Never reference `data` in the
empty branch.

## UI conventions

- Field help: use a `?` button next to the label text. For block labels insert
  it before the input; for inline checkbox labels append it at the end.
- Auto bounds/cells: compute from preview, fill the field, lock it; unlock on
  uncheck. Manual extents only take over when all four are filled.
- Auto cell size must mirror the backend: 5% pad, longest side, target cells.
- Cross-section: default line after solve; drag endpoints or the whole line;
  inverse map coordinates must include zoom and pan.
- Vertical exaggeration: logarithmic slider, auto target roughly 30% of the
  longest horizontal extent, clamped; `Auto` recomputes.
- Progress: stage labels + elapsed time. The C++ solve is one call, so the bar
  is indeterminate while `stage == "solving"`.
- Do not add a second build system or a frontend framework.

## Test

API:

```bash
cd workbench
PYTHONPATH="$PWD:$PWD/.site:$PWD/../build-ci/bin" \
SURFIT_BIN="$PWD/../build-ci/bin" \
python3 tests/test_app.py
```

Browser (install once if `node_modules` is absent):

```bash
cd workbench
npm install
PLAYWRIGHT_BROWSERS_PATH="$PWD/.pw-browsers" \
  npx playwright install chromium
PLAYWRIGHT_BROWSERS_PATH="$PWD/.pw-browsers" \
  node tests/browser_check.js
```

Run the relevant `browser_areas.js`, `browser_surfaces.js`,
`browser_bounds.js`, `browser_autocell.js`, `browser_section_drag.js`,
`browser_fullscreen.js`, `browser_help.js` or `browser_progress.js` after a
change in that area. Do not claim a UI change is done without a browser check.

See [LESSONS.md](LESSONS.md) for the mistakes that produced these rules.
