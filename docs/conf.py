"""Sphinx configuration for surfit.

The documentation is kept as two parallel source trees, ``docs/en`` and
``docs/ru``, which share this file.  A page has the same name in both trees,
and that is what lets the language switcher point at its counterpart;
``docs/check_docs.py`` fails the build when the two drift apart.

Build both languages with ``docs/build.sh``.
"""

import os

from pygments.lexer import include
from pygments.lexers.tcl import TclLexer
from pygments.token import Keyword, Text, Whitespace

project = "surfit"
author = "M. V. Dmitrievsky, V. N. Kutrunov"
copyright = "2002-2007 M. V. Dmitrievsky & V. N. Kutrunov"

extensions = ["sphinx_tabs.tabs"]

templates_path = ["_templates"]
html_static_path = ["_static"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.md"]

root_doc = "index"

# One of the two trees is built per invocation: sphinx-build -D language=ru ...

try:
    import sphinx_rtd_theme  # noqa: F401

    html_theme = "sphinx_rtd_theme"
    html_theme_options = {
        "navigation_depth": 3,
        "collapse_navigation": False,
    }
except ImportError:  # the theme is optional, alabaster ships with Sphinx
    html_theme = "alabaster"

html_title = "surfit"
html_short_title = "surfit"
html_show_sourcelink = False

LANGUAGE_LABELS = {"en": "English", "ru": "Русский"}


class SurfitTclLexer(TclLexer):
    """Pygments' Tcl lexer, with one fix.

    The generated example scripts end many lines with a space.  In Pygments'
    lexer the trailing space is matched by ``\\s+`` in the ``params`` state,
    which swallows the newline as well, so the state never pops and every
    following ``#`` becomes an error token.  Matching the spaces separately
    leaves the newline for the pop rule, and the scripts highlight cleanly.
    """

    name = "Tcl (surfit)"
    aliases = ["tcl-src"]
    tokens = dict(TclLexer.tokens)
    tokens["params"] = [
        (r"[ \t]+", Whitespace),
        (r"\n", Text, "#pop"),
        (r";", Keyword, "#pop"),
        (r"(else|elseif|then)\b", Keyword),
        include("basic"),
        include("data"),
    ]


def _add_language_switcher(app, pagename, templatename, context, doctree):
    """Hands the template the URL of the same page in the other language.

    Both trees are built into ../<lang>/, so the counterpart of page
    ``a/b`` sits at ``<depth>/<other>/a/b.html`` plus the two steps back
    up to the language roots.
    """
    if app.builder.format != "html":
        return

    current = app.config.language or "en"
    other = "ru" if current == "en" else "en"
    depth = pagename.count("/") + 1

    context["language_switcher_url"] = "%s%s/%s.html" % (
        "../" * depth, other, pagename)
    context["language_switcher_label"] = LANGUAGE_LABELS[other]
    context["language_current_label"] = LANGUAGE_LABELS[current]


def setup(app):
    app.connect("html-page-context", _add_language_switcher)
    app.add_css_file("custom.css")
    app.add_js_file("copy_code.js")
    app.add_lexer("tcl-src", SurfitTclLexer)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
