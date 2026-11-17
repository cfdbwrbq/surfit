#!/usr/bin/env bash
# Build manylinux wheels in the official pypa image, without NetCDF/curl.
#
# Default: manylinux2014 (glibc 2.17), CPython 3.9-3.13 (3.8 is gone from the image).
#   sudo ci/build-manylinux.sh
#
# Override the image for manylinux_2_28:
#   IMAGE=quay.io/pypa/manylinux_2_28_x86_64 PLAT=manylinux_2_28_x86_64 \
#     OUT=manylinux_2_28 sudo -E ci/build-manylinux.sh
set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
IMAGE="${IMAGE:-quay.io/pypa/manylinux2014_x86_64}"
PLAT="${PLAT:-manylinux2014_x86_64}"
OUT="${OUT:-manylinux2014}"
PYTHONS="${PYTHONS:-cp39-cp39 cp310-cp310 cp311-cp311 cp312-cp312 cp313-cp313}"
HOST_UID="${SUDO_UID:-$(id -u)}"
HOST_GID="${SUDO_GID:-$(id -g)}"

rm -rf "$REPO/dist/$OUT"
mkdir -p "$REPO/dist/$OUT"
docker run --rm \
  -v "$REPO":/work \
  -e HOST_UID="$HOST_UID" \
  -e HOST_GID="$HOST_GID" \
  -e PYTHONS="$PYTHONS" \
  -e PLAT="$PLAT" \
  -e OUT="$OUT" \
  "$IMAGE" bash -lc '
    set -euo pipefail
    for ds in /opt/rh/devtoolset-9 /opt/rh/devtoolset-10 /opt/rh/devtoolset-11 \
          /opt/rh/gcc-toolset-10 /opt/rh/gcc-toolset-11 /opt/rh/gcc-toolset-12; do
      if [ -f "$ds/enable" ]; then
        # The scl/devtoolset enable scripts read unset variables such as MANPATH.
        set +u
        source "$ds/enable"
        set -u
        break
      fi
    done

    if command -v dnf >/dev/null 2>&1; then
      dnf install -y -q zlib-devel libjpeg-turbo-devel >/dev/null 2>&1 || true
    elif command -v yum >/dev/null 2>&1; then
      yum install -y -q zlib-devel libjpeg-turbo-devel >/dev/null 2>&1 || true
    fi

    cp -a /work /tmp/src
    cd /tmp/src
    rm -rf build dist

    for py in $PYTHONS; do
      P=/opt/python/$py/bin
      if [ ! -x "$P/python" ]; then
        echo "==> skip $py (not in image; available: $(ls /opt/python 2>/dev/null | tr "\n" " "))"
        continue
      fi
      case "$py" in
        cp38*|cp39*) SB="scikit-build-core<0.11"; PB="pybind11<3" ;;
        *) SB="scikit-build-core"; PB="pybind11" ;;
      esac
      echo "==> $py"
      "$P/pip" install -q --upgrade pip
      "$P/pip" install -q "$SB" "$PB" auditwheel
      rm -rf "/tmp/wheels-$py"
      "$P/pip" wheel . --no-deps --no-build-isolation \
        -w "/tmp/wheels-$py" \
        --config-settings=cmake.define.CMAKE_DISABLE_FIND_PACKAGE_NetCDF=ON \
        --config-settings=cmake.define.CMAKE_INSTALL_RPATH=\$ORIGIN \
        --config-settings=cmake.define.CMAKE_BUILD_WITH_INSTALL_RPATH=ON

      rm -rf "/tmp/extract-$py"
      mkdir -p "/tmp/extract-$py"
      unzip -q "/tmp/wheels-$py"/surfit-*.whl -d "/tmp/extract-$py"
      LD_LIBRARY_PATH="/tmp/extract-$py/surfit${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
        "$P/auditwheel" repair "/tmp/wheels-$py"/surfit-*.whl \
        -w "/work/dist/$OUT" --plat "$PLAT"
    done

    chown -R "$HOST_UID:$HOST_GID" "/work/dist/$OUT"
  '

ls -lh "$REPO/dist/$OUT"
