#!/usr/bin/env bash
# Build a self-contained source bundle with an optional local wheelhouse.
set -euo pipefail

cd "$(dirname "$0")"
VERSION="${VERSION:-$(date +%Y%m%d)}"
OUT="${OUT:-dist}"
STAGE="$OUT/surfit-workbench-$VERSION"
WHEELS="${WHEELS:-../wheels-manylinux2014}"

rm -rf "$STAGE"
mkdir -p "$STAGE"

cp -a backend frontend examples tests "$STAGE"/
cp README.md PLAN.md 3D_WATCH.md requirements.txt requirements-geo.txt \
   run.sh Makefile "$STAGE"/
rm -rf "$STAGE"/backend/__pycache__ "$STAGE"/tests/__pycache__
rm -rf "$STAGE"/tests/screenshots

if [ -d "$WHEELS" ] && ls "$WHEELS"/surfit-*.whl >/dev/null 2>&1; then
  mkdir -p "$STAGE/wheels"
  cp "$WHEELS"/surfit-*.whl "$STAGE/wheels"/
fi

cat > "$STAGE/bootstrap.sh" <<'BOOT'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install --target .site -r requirements.txt
if ls wheels/surfit-*.whl >/dev/null 2>&1; then
  python3 -m pip install --target .site --no-index --find-links wheels --no-deps surfit
else
  echo "no wheel bundled; install surfit separately and set SURFIT_BIN" >&2
fi
BOOT
chmod +x "$STAGE/bootstrap.sh" "$STAGE/run.sh"
( cd "$STAGE" && zip -qr "../surfit-workbench-$VERSION.zip" . )
printf '%s\n' "$OUT/surfit-workbench-$VERSION.zip"
