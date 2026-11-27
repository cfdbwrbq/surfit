# Workbench lessons

### Wrong entry point
- **Symptom:** UI changes were invisible because the browser served the old
  sibling `surfit-studio/` copy.
- **Root cause:** the old standalone repository was still the command in the
  terminal after workbench moved into `surfit/workbench`.
- **Rule:** start only `surfit/workbench/run.sh`; verify the path before
  debugging missing UI features.
- **Evidence:** user report after 3.7.5 workbench work.

### Help icons landed under inputs
- **Symptom:** labels looked like `Cell size` / input / `?` on a separate line.
- **Root cause:** the help button was appended after a block-level input.
- **Rule:** insert help before the input for block labels; append only for
  inline checkbox labels.
- **Evidence:** `fix: align field help with labels`, screenshot review.

### Empty manual extent parsed as zero
- **Symptom:** auto cell size stayed at 1 even after preview.
- **Root cause:** `Number("")` is `0`, so `Number.isFinite` treated an empty
  manual extent as a valid zero-width extent.
- **Rule:** test `value !== ""` before converting; only use manual extents when
  all four are non-empty and finite.
- **Evidence:** `browser_autocell.js` before/after 0.055 -> 0.11.

### `data` undefined when all files are removed
- **Symptom:** clearing the file list could throw while refreshing area/surface
  state.
- **Root cause:** the no-active branch of `schedulePreview()` referenced the
  preview `data` object that is only defined in the success branch.
- **Rule:** explicitly clear dynamic panels with empty inputs in the no-active
  branch; never reuse the success-path variable.
- **Evidence:** release-prep browser checks.

### Server restart vs static reload
- **Symptom:** stage progress showed `running` instead of the new stages.
- **Root cause:** the running uvicorn process predated the backend change;
  static JS reloaded, Python did not.
- **Rule:** restart uvicorn after backend changes; reload only for frontend
  changes.
- **Evidence:** progress test on :8011 after restart.
