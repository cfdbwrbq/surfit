# Legacy cleanup — second pass (3.7.3)

The first pass (`504dc90`) removed the old Doxygen `doc/` tree, the Windows
NSIS installer, the Windows build scripts, `Hints`, `short_description` and the
root `build.sh`. This pass removes the few files left that nothing in the
tracked tree refers to, and records what was deliberately kept.

The deletions below are part of the cleanup commit; this file records the
evidence and the files deliberately kept.

## Removed now (4 files, ~3.6 KiB)

| File | Why it is safe |
| --- | --- |
| `src/surfit_cmd/src/resource.h` | MSVC resource IDs (`IDI_ICON1`) for `surfit_cmd.rc`. That `.rc` was deleted in `4ecc7b1` (2015, "moving to cmake build system"); no source includes this header and CMake has no resource compiler stage. |
| `src/surfit_cmd/src/icon1.ico` | Windows executable icon referenced only by that deleted `.rc`. No `.rc`, `.iss` or `.nsi` remains, and no CMake rule or workflow embeds an icon. |
| `examples/surfit_io/run_before_test` | 2007 pre-CMake helper (`b33c8ae`) that deleted example outputs in place. Tests now copy a corpus into a scratch directory (`run_tcl_suite.py`, `test_examples.py`), so nothing calls it. |
| `examples/surfit_io/run_before_test.bat` | Windows counterpart of the above (`44f4857`, 2007). The Windows build/installer was removed in the first pass and CI does not cover Windows/MSVC (`docs/en/development.rst`), so nothing consumes it. |

`src/windows_installer/` is already gone. No tracked `.rc`, `.iss`, `.nsi`,
`.bat` or `.cmd` file remains; the only `.ico` was the one removed here.

## Kept, and why

- **Tcl (until 3.8).** `src/tclsurfit/` (9 files), `src/surfit_cmd/` (2 files:
  the Tcl CLI), 53 `*_tcl.*` binding units, 12 `.i` interfaces, the Tcl example
  corpora, `docs/en|ru/tcl.rst`, `docs/en|ru/migration.rst` and the goldens are
  all part of the still-supported Tcl front end. `docs/en/installation.rst`
  states that 3.7.x is the last Tcl-capable line and 3.8 removes it.
- **Goldens.** `src/pysurfit/tests/golden/3.7.2` (44 files) are test references.
- **`docs/_static` (51 files).** All 51 are referenced — 47 from at least two
  README/RST sites, `cover.svg` from `docs/ru/index.rst`, and
  `copy_code.js`, `custom.css`, `logo.svg` from `docs/conf.py`. No deletion.
- **Example and test data.** `examples/surfit/tests/data`, the realworld
  corpora, the `surfit_io` inputs and the SRTM tile are untouched. 78 assets
  have no literal reference, and every one is under `examples/`:
  - 69 in `examples/surfit/realworld/`: `zones/*.c*`, `data/filter/filter*.ctr`,
    `data/faults/fault*.ctr`, `volumetrics/isos/iso_*` and shapefile
    companions, all loaded by globs or by the shapefile library;
  - 5 in `examples/freeflow/press2/` (`VNK_1.CTR`, `VNK_2.CTR`, `ZAM2.CTR`,
    `ZAM3.CTR`, `ZAM4.CTR`) — not read by the current scripts, example data;
  - 4 in `examples/surfit_io/shp/const_cntr/`: `isos.dbf` and `isos.shx` are
    shapefile companions, while `isos.htab` and `isos.hshp` are 2007
    `HISTORY_VERSION_1.02` sidecars with Windows paths and no reader in `src/`;
    kept because they sit in example data.
- **Vendor code.** `src/surfit/src/third_party/cdt/`, `shapelib/`,
  `src/surfit_io/src/EasyBmp/`, `src/surfit_io/src/shapelib/`,
  `src/globe/src/minizip/` and `src/sstuff/src/ptypes/` are dependencies.
- **Root files.** `README*.md`, `AI_DISCLOSURE.md`, `CAPABILITIES*.md`,
  `LICENSE`, `pyproject.toml`, `requirements-dev.txt`, `.flake8` and
  `.gitignore` are referenced or are conventional tool entry points (the three
  READMEs link each other and `pyproject.toml` uses `README.md`).
- **`.agents/skills/surfit/`.** `SKILL.md` links `RULES.md`; this is the tracked
  usage skill (the ignored sibling skills are local only).

### Unreferenced but kept

- `examples/globe/canyon/readme.txt` — unreferenced by name, but it explains
  the missing USA DTM and nine SRTM tiles and why those scripts are not ported.
- `examples/surfit/realworld/example3/saratov_simple.tcl` — no literal
  reference, but `run_tcl_suite.py --sequential` discovers every `.tcl` in the
  directory and it is covered by `golden/3.7.2/traces/example3__group.py`.
- 12 more `examples/freeflow/press2/` text files with no reference:
  `Q_2001_del.txt`, `Q_2002.txt`, `debits.txt`, `grd_line.txt`,
  `wPzab_2001.txt`, and seven under `lines/`: `P_2001_236_diag1.txt`,
  `P_2001_236_diag2.txt`, `Q_2001_236_diag1.txt`, `Q_2001_236_diag2.txt`,
  `Q_2001_236_hor.txt`, `Q_2001_236_ver.txt`, `Q_2001_258.txt`. They are
  example data; only the inputs the two `map_*` scripts read are live.
- `.github/workflows/docs.yml`, `.github/workflows/wheels.yml`, `docs/conf.py`,
  `pyproject.toml` and `src/cmake/FindNetCDF.cmake` have no literal referrer by
  design: GitHub Actions runs workflows by path, Sphinx and pip read their
  conventional files, and CMake finds `FindNetCDF.cmake` through
  `CMAKE_MODULE_PATH` + `find_package(NetCDF)`.

## Exact no-reference check used

The inventory is `git ls-files`. For each candidate, both the repository path
and the basename were searched in every tracked text file (`README`, RST,
source, CMake, workflows, scripts), with the file itself excluded:

```bash
git grep -l -F '<basename>' -- ':!<path>'
git grep -l -F '<path>'     -- ':!<path>'
```

For `docs/_static` every asset was checked the same way:

```bash
for f in $(git ls-files docs/_static); do
    b=$(basename "$f")
    git grep -q -F "$b" -- ':!docs/_static' && echo "ok $b"
done
# 51/51 ok
```

Deletion evidence, all empty:

```bash
git grep -n -F 'resource.h'  -- ':!src/surfit_cmd/src/resource.h'
git grep -n -F 'icon1.ico'   -- ':!src/surfit_cmd/src/icon1.ico'
git grep -n -F 'IDI_ICON1'   -- ':!src/surfit_cmd/src/resource.h'
git grep -n -F 'run_before_test' -- ':!examples/surfit_io/run_before_test' \
                                    ':!examples/surfit_io/run_before_test.bat'
git ls-files | grep -E '\.(rc|rc2|iss|nsi|nsh|manifest)$'   # none
git grep -n -E 'enable_language\(RC|CMAKE_RC'               # none
```

A wider scan of all tracked assets (images, data, shapefile companions) found
79 files with no literal reference before this pass. After removing
`icon1.ico`, 78 remain, all under `examples/` as described above.

## Remains for 3.8 (Tcl removal checklist)

These stay now and are the work of the 3.8 release, not of this cleanup:

- `src/tclsurfit/` — 9 files: `CMakeLists.txt` and 8 `.i` interfaces.
- `src/surfit_cmd/` — 2 files: `CMakeLists.txt` and the `Tcl_Main` CLI.
- 53 `*_tcl.*` binding units (26 surfit, 13 surfit_io, 8 freeflow, 6 globe),
  12 `.i` files, and the three checked-in SWIG wrappers
  (`freeflow_wrap.cxx`, `globe_wrap.cxx`, `surfit_io_wrap.cxx`).
- Tcl example corpora: `examples/surfit/` (196 files, including `tests/` and
  `realworld/`), `examples/freeflow/` (48), `examples/globe/` (10),
  `examples/surfit_io/` (42 after this pass) and `examples/run_all.tcl`.
- `docs/en/tcl.rst`, `docs/ru/tcl.rst`, `docs/en/migration.rst`,
  `docs/ru/migration.rst`; `docs/*/commands.rst` is generated from the SWIG
  `.i` files by `docs/make_command_reference.py` and needs regeneration.
- Tcl-driven tests: `src/pysurfit/tests/run_tcl_suite.py`,
  `src/pysurfit/tests/test_examples.py`, `ci/check.sh --full`, and
  `src/pysurfit/tests/golden/3.7.2/` (44 files).

## Verification

```text
git diff --check                       -> clean (no output)
PYTHONPATH=$PROJECT/.docsdeps python3 docs/check_docs.py
                                       -> OK   15 pages, both trees in step (exit 0)
```

No file was removed under `docs/_static`, so the docs sources are unchanged;
the build was still run to prove it:

```text
PYTHONPATH=$PROJECT/.docsdeps docs/build.sh
-> both trees build, exit 0, no warnings
```

The project self-check also passes (it validates the skill links, both docs
trees and the importable API):

```text
SURFIT_BIN=build-ci/bin PYTHONPATH=$PROJECT/.docsdeps \
    python3 ci/selfcheck.py
-> skills: 4 valid, links present
   OK   15 pages, both trees in step
   silent exceptions: none in the package
   all selfchecks passed
```

