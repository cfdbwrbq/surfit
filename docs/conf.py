"""Sphinx configuration for surfit.

The documentation is kept as two parallel source trees, ``docs/en`` and
``docs/ru``, which share this file.  They are built into ``../<lang>/``, and
the theme's locale widget switches between the two roots;
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

html_static_path = ["_static"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.md"]

root_doc = "index"

# One of the two trees is built per invocation: sphinx-build -D language=ru ...

version = "3.1"
release = "3.1"

try:
    import sphinx_nefertiti  # noqa: F401

    html_theme = "sphinx_nefertiti"
except ImportError:  # the theme is optional, alabaster ships with Sphinx
    html_theme = "alabaster"

HEADER_LINKS = {
    "en": [
        {"text": "First steps", "link": "first_steps"},
        {"text": "Python", "link": "python"},
        {"text": "Tcl", "link": "tcl"},
        {"text": "Formats", "link": "formats"},
    ],
    "ru": [
        {"text": "Первые шаги", "link": "first_steps"},
        {"text": "Python", "link": "python"},
        {"text": "Tcl", "link": "tcl"},
        {"text": "Форматы", "link": "formats"},
    ],
}

html_theme_options = {
    "style": "green",
    "project_name_font": "Montserrat",
    "monospace_font": "Fira Code",
    "monospace_font_size": "1.0rem",
    "documentation_font_size": "1.1rem",
    "doc_headers_font": "Montserrat",
    "pygments_light_style": "pastie",
    "pygments_dark_style": "dracula",
    "logo": "logo.svg",
    "logo_width": 28,
    "logo_height": 28,
    "logo_alt": "surfit",
    "repository_url": "https://github.com/mdmitr/surfit",
    "repository_name": "surfit",
    "current_version": release,
    "header_links": HEADER_LINKS["en"],
    "locales": [
        ("en", "../en/"),
        ("ru", "../ru/"),
    ],
}

html_css_files = ["custom.css"]
html_js_files = ["copy_code.js"]
html_title = "surfit"
html_short_title = "surfit"
html_show_sourcelink = False

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


def _localize_header_links(app, config):
    """The conf file is shared by both trees; the -D language comes later."""
    language = config.language or "en"
    options = dict(config.html_theme_options or {})
    options["header_links"] = HEADER_LINKS.get(language, HEADER_LINKS["en"])
    config.html_theme_options = options


def setup(app):
    app.connect("config-inited", _localize_header_links)
    app.add_lexer("tcl-src", SurfitTclLexer)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
