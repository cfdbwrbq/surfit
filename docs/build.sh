#!/bin/sh
#
# Builds the documentation in both languages.
#
#   docs/build.sh            both trees, English first
#   docs/build.sh en         one language
#
# The two trees are built into _build/html/<lang>/ and a root page is written
# that redirects to English.
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
OUT="$HERE/_build/html"
# A command, not a path: the default runs Sphinx through the interpreter so an
# installation in a non-default prefix works with PYTHONPATH set.
SPHINX=${SPHINX:-python3 -m sphinx}

LANGS=${*:-"en ru"}

for lang in $LANGS; do
    echo "==> building $lang"
    # shellcheck disable=SC2086
    $SPHINX -q -b html -c "$HERE" -D language="$lang" "$HERE/$lang" "$OUT/$lang"
done

if [ "$LANGS" = "en ru" ]; then
    cat > "$OUT/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>surfit</title>
<meta http-equiv="refresh" content="0; url=en/index.html">
<link rel="canonical" href="en/index.html">
</head>
<body>
<p>Redirecting to the <a href="en/index.html">English documentation</a>.</p>
</body>
</html>
HTML
fi

echo "==> done: $OUT/index.html"
