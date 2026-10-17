"""HTML viewer for a gridded surface, drawn in the browser with d3.

The engine used to produce PostScript through CreEPS, which ties the output to a
printer-oriented format and to a C++ library.  A page is easier to share, zoom
and inspect: this renders the grid as a filled contour map with a readout, and
the data is embedded, so the file stands on its own apart from the d3 script.

The contour computation lives in ``viewer.js``, which is also loaded by the
tests, so it can be checked without a browser.
"""

import base64
import html
import json
import os

import numpy as np

from . import _surfit as _core

#: d3 is fetched when the page is opened; pass ``d3_url`` to point at a local
#: copy when the machine viewing the file has no network access.
DEFAULT_D3_URL = "https://cdn.jsdelivr.net/npm/d3@7"

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ margin: 0; padding: 24px; font: 14px/1.5 system-ui, sans-serif;
          color: #1a1a1a; background: #fff; }}
  h1 {{ font-size: 18px; margin: 0 0 16px; }}
  #surfit-view svg {{ max-width: 100%; height: auto; border: 1px solid #e1e4e5;
                      border-radius: 4px; }}
  .surfit-source {{ margin-top: 12px; font-size: 12px; color: #666; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div id="surfit-view"></div>
<div class="surfit-source">surfit {version} &middot; {count_x} x {count_y} nodes,
{defined} defined &middot; rendered with d3</div>
<script src="{d3_url}"></script>
<script>window.SURFIT_DATA = {data};</script>
<script>window.SURFIT_CONFIG = {config};</script>
<script>{script}</script>
<script>
  SurfitViewer.render(document.getElementById("surfit-view"),
                      window.SURFIT_DATA, window.SURFIT_CONFIG, window.d3);
</script>
</body>
</html>
"""


def _viewer_script():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer.js")
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _payload(values, extent):
    """Base64 of the grid, shape checks included.

    Float64 keeps the page lossless; a viewer is read by eye, but a surprise in
    the data path is not worth saving a few hundred kilobytes on.
    """
    array = np.ascontiguousarray(values, dtype="<f8")
    count_x = int(extent["count_x"])
    count_y = int(extent["count_y"])
    if array.shape != (count_y, count_x):
        raise ValueError(
            "surface is %s but its extent says %d x %d"
            % (array.shape, count_y, count_x))
    encoded = base64.b64encode(array.tobytes()).decode("ascii")
    defined = int(np.count_nonzero(~np.isclose(
        array, np.finfo(np.float32).max, rtol=1e-6)))
    return encoded, defined


def render_html(values, extent, title="surfit surface", levels=12,
                show_lines=True, size=820, d3_url=None):
    """Builds a self-contained HTML page for one grid.

    :param values: a ``(count_y, count_x)`` array, as returned by ``values()``
    :param extent: the matching geometry, as returned by ``surf_extent()``
    :param levels: number of filled contour bands
    :param d3_url: where to load d3 from when the page is opened
    """
    encoded, defined = _payload(values, extent)

    data = {
        "values": encoded,
        "count_x": int(extent["count_x"]),
        "count_y": int(extent["count_y"]),
        "min_x": float(extent["min_x"]),
        "max_x": float(extent["max_x"]),
        "min_y": float(extent["min_y"]),
        "max_y": float(extent["max_y"]),
        "step_x": float(extent["step_x"]),
        "step_y": float(extent["step_y"]),
        "undef": float(np.finfo(np.float32).max),
        "encoding": "base64 float64 little-endian, row-major, row 0 is min_y",
    }
    config = {
        "title": title,
        "levels": int(levels),
        "show_lines": bool(show_lines),
        "size": int(size),
    }

    return _TEMPLATE.format(
        title=html.escape(title),
        version="3.1",
        count_x=data["count_x"],
        count_y=data["count_y"],
        defined=defined,
        d3_url=d3_url or DEFAULT_D3_URL,
        data=json.dumps(data),
        config=json.dumps(config),
        script=_viewer_script(),
    )


def viewer(pos=-1, **kwargs):
    """HTML page for a surface in memory; the last one by default.

    ``-1`` and any other negative index count back from the most recent
    surface, the same way ``values()`` does.
    """
    if pos < 0:
        pos += _core.surf_count()
        if pos < 0:
            raise KeyError("no surfaces in memory")
    return render_html(_core.surf_values(pos), _core.surf_extent(pos), **kwargs)


def save_viewer(path, pos=-1, **kwargs):
    """Writes the page for a surface to ``path`` and returns the path."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(viewer(pos, **kwargs))
    return path
