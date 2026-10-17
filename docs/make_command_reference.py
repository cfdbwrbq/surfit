#!/usr/bin/env python3
"""Generates the command reference from the interface files and the headers.

    python3 docs/make_command_reference.py          # rewrite both pages
    python3 docs/make_command_reference.py --check  # fail if they are stale

The list of commands comes from the SWIG interface files under ``src``: every
``.i`` file that declares a function contributes one command, and the set matches
the commands the built Tcl front end reports (the test suite checks that
separately).  The Tcl syntax, the description, the parameters and the example
come from the Doxygen comments in the headers, which is also where the original
manual's command pages came from.

The two pages are the same reference in both languages: the entries are the
commands, their syntax and the English descriptions from the header comments;
only the title, the introduction and the section names are translated.
"""
import glob
import html
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EN = os.path.join(HERE, "en", "commands.rst")
RU = os.path.join(HERE, "ru", "commands.rst")

#: The header comments misspell a few command names; map them to the real one.
DOC_ALIASES = {
    "dem_load_dmt": "dem_load_dtm",
    "pnts_inverse_transfort": "pnts_inverse_transform",
    "flow_point": "flow_points",
    "masks_info": "mask_info",
}

#: Documentation blocks for commands that this build does not have; the
#: interface files are the authority, so these are ignored.
DOC_IGNORED = {"surf_load_png", "surf_save_png"}

#: Commands the headers do not describe, with a one-line description each.
#: They are kept here rather than in the generated page so a regeneration keeps
#: them; the text says what the implementation does, nothing more.
SUPPLEMENT = {
    "clear_rules": "Drops the gridding rules but keeps the loaded data.",
    "get_current_solver_long_name": "Long name of the solver chosen by ``set_solver``.",
    "get_current_solver_short_name": "Short name of the solver chosen by ``set_solver``.",
    "get_solver_long_name": "Long name of the solver at the given position.",
    "get_solver_short_name": "Short name of the solver at the given position.",
    "get_solvers_count": "Number of available solvers.",
    "hist_del": "Removes the histograms matching the name.",
    "hist_from_pnts": "Builds a histogram from the values of a points dataset.",
    "hist_from_surf": "Builds a histogram from the values of a surface.",
    "hist_getName": "Names of the histograms in memory, or of those matching the pattern.",
    "hist_setName": "Renames a histogram.",
    "hist_size": "Number of histograms in memory.",
    "hists_info": "Prints a summary of the histograms in memory.",
    "lcm_simple_add": "Adds the conservation-of-mass rule with a weight.",
    "log_clear": "Truncates the log file.",
    "log_open": "Opens the log file (``surfit.log`` by default) for appending "
                "and sets the log level.",
    "putlog": "Writes a message to the log at the message level.",
    "set_solver": "Selects the linear solver by short name: ``cg``, ``jcg``, "
                  "``rf``, ``jacobi`` or ``ssor``.",
    "show_c": "Prints the copying conditions.",
    "show_w": "Prints the warranty disclaimer.",
    "smooth_contour_add": "Adds the contour-smoothing rule with a weight.",
    "solvers_info": "Prints the available solvers, long name and short name.",
    "surf_adj_hist": "Adjusts the surface so that its histogram matches the "
                     "given one.",
    "surfit": "Runs the gridding algorithm on the current task; if no rules "
              "were added, default rules are created from the loaded data.",
    "triangulate": "Builds a surface by triangulating the loaded points.",
    "types_info": "Returns the list of data types the front end knows.",
}

SECTION_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def read(path):
    with open(path, encoding="latin-1") as handle:
        return handle.read()


def strip_comments(text):
    text = re.sub(r"%\{.*?%\}", "", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def split_params(text):
    """Splits a C++ parameter list at top-level commas."""
    parts, depth, quote, current = [], 0, False, []
    for char in text:
        if char == '"' and (not current or current[-1] != "\\"):
            quote = not quote
        if not quote and char in "([{":
            depth += 1
        elif not quote and char in ")]}":
            depth -= 1
        if char == "," and not quote and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        parts.append("".join(current))
    return parts


def parse_signature(params):
    """(name, default) for each parameter of a C++ declaration."""
    parsed = []
    for param in split_params(params):
        param = param.strip()
        if not param or param == "void":
            continue
        default = None
        if "=" in param:
            param, default = param.split("=", 1)
            default = default.strip()
        match = re.search(r"([A-Za-z_]\w*)\s*(\[\s*\])?\s*$", param.strip())
        if match:
            parsed.append((match.group(1), default))
    return parsed


def tcl_syntax(name, params):
    """`name arg [optional]` from a C++ declaration's parameter list."""
    words = []
    for arg, default in parse_signature(params):
        words.append("[%s]" % arg if default is not None else arg)
    return " ".join([name] + words)


def declaration(name, params):
    """`name(arg, arg=default)` from a C++ declaration."""
    parts = []
    for arg, default in parse_signature(params):
        parts.append("%s=%s" % (arg, default) if default is not None else arg)
    return "%s(%s)" % (name, ", ".join(parts))


def interface_commands():
    """Every command declared by a SWIG interface file."""
    commands = {}
    for path in sorted(glob.glob(os.path.join(REPO, "src", "**", "*.i"),
                                  recursive=True)):
        text = strip_comments(read(path))
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue
            if line in ("namespace surfit {", "};", "}"):
                continue
            lines.append(line)
        for statement in " ".join(lines).split(";"):
            statement = statement.strip()
            if not statement or statement.startswith("extern "):
                continue
            match = re.match(
                r"^(?:surfit::)?[\w:<>,\s*&]+?\b([A-Za-z_]\w*)\s*\((.*)\)$",
                statement)
            if not match:
                continue
            name, params = match.group(1), match.group(2)
            if name in commands:
                continue
            defaults = {}
            for arg, default in parse_signature(params):
                key = re.sub(r"[^a-z0-9]", "", arg.lower())
                defaults[arg] = default
                defaults[key] = default
                defaults[key.rstrip("s")] = default
            commands[name] = {
                "name": name,
                "syntax": tcl_syntax(name, params),
                "declaration": declaration(name, params),
                "defaults": defaults,
                "description": "",
                "params": [],
                "example": "",
                "documented": False,
            }
    return commands


def ref_label(target):
    """A readable label for a Doxygen reference target."""
    target = target.rstrip("()")
    for prefix in ("d_", "f_", "tcl_"):
        if target.startswith(prefix):
            return target[len(prefix):]
    return target


def clean(text):
    """Turns the Doxygen fragments into plain RST prose."""
    text = re.sub(r"\\li(?=\s|$)", "\n- ", text)
    text = re.sub(r'\\ref\s+\S+\s+"([^"]*)"', r"\1", text)
    text = re.sub(r"\\ref\s+(\S+)(?=\s|$)",
                  lambda match: ref_label(match.group(1)), text)
    text = re.sub(r"\\c\s+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\\f\$\s*(.*?)\s*\\f\$", r":math:`\1`", text, flags=re.S)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def paragraph(text, indent):
    """Wraps prose to a readable width with the given indent."""
    import textwrap
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = " ".join(block.split())
        if not block:
            continue
        if block.startswith("- "):
            out.append(textwrap.fill(block, width=76,
                                     initial_indent=" " * indent,
                                     subsequent_indent=" " * (indent + 2)))
        else:
            out.append(textwrap.fill(block, width=76,
                                     initial_indent=" " * indent,
                                     subsequent_indent=" " * indent))
    return "\n\n".join(out)


def documented_blocks():
    """Reads every Doxygen block that documents a Tcl syntax."""
    found = {}
    for path in sorted(glob.glob(os.path.join(REPO, "src", "**", "*.h"),
                                 recursive=True)):
        text = read(path)
        for match in re.finditer(r"/\*!(.*?)\*/", text, re.S):
            body = match.group(1)
            marker = re.search(r"\\par\s+Tcl syntax:?\s*", body, re.I)
            if not marker:
                continue
            rest = body[marker.end():]
            syntax_lines = []
            for line in rest.splitlines():
                stripped = line.strip()
                if not stripped:
                    if syntax_lines:
                        break
                    continue
                if stripped.startswith(("\\par", "\\param", "\\li", "\\note")):
                    break
                syntax_lines.append(stripped)
            if not syntax_lines:
                continue
            syntax = clean(" ".join(syntax_lines))
            # The declaration that follows the comment is the authority: a few
            # blocks have a generic or copy-pasted Tcl syntax line (grid_get2 is
            # documented as "grid_get", surf_div as "surf_mult"), and the
            # following prototype names the function those docs belong to.
            following = text[match.end():match.end() + 400]
            following = following.split(";", 1)[0]
            declaration = re.search(r"\b([A-Za-z_]\w*)\s*\(", following)
            function = re.search(r"\\fn\s+[^(\n]*?\b([A-Za-z_]\w*)\s*\(",
                                 body)
            if declaration:
                name = declaration.group(1)
            elif function:
                name = function.group(1)
            else:
                name = syntax.split()[0]
            description = ""
            desc = re.search(r"\\par\s+Description:\s*", body)
            if desc:
                tail = body[desc.end():]
                cut = re.search(r"\n\s*\\(?:par|param|note)\b", tail)
                description = clean(tail[:cut.start()] if cut else tail)
            params = []
            for param in re.finditer(
                    r"\\param\s+(\w+)\s+(.*?)(?=\n\s*\\(?:param|par|note)\b|\Z)",
                    body, re.S):
                params.append((param.group(1), clean(param.group(2))))
            example = ""
            example_match = re.search(
                r"\\par\s+Example\s*\n(.*?)(?=\n\s*\\(?:par|param)\b|\Z)",
                body, re.S)
            if example_match:
                example = clean(example_match.group(1))
            record = {
                "syntax": syntax,
                "description": description,
                "params": params,
                "example": example,
                "path": path,
            }
            target = DOC_ALIASES.get(name, name)
            if name in DOC_IGNORED or target in DOC_IGNORED:
                continue
            # Two headers may document the same command; keep the fuller one.
            old = found.get(target)
            if old is None or len(description) > len(old["description"]):
                found[target] = record
    return found


def escape_rst(text):
    """Escapes the characters that would otherwise be RST markup."""
    return re.sub(r"([*|])", r"\\\1", text)


def render_entry(command):
    lines = ["``%s``" % command["name"]]
    lines.append("    **Syntax:** ``%s``" % command["syntax"])
    if command["description"]:
        lines.append("")
        lines.append(paragraph(command["description"], 4))
    if command["params"]:
        lines.append("")
        for name, text in command["params"]:
            text = re.sub(r"^=\s*", "", " ".join(text.split()))
            key = re.sub(r"[^a-z0-9]", "", name.lower())
            defaults = command.get("defaults", {})
            default = defaults.get(key)
            if default is None:
                default = defaults.get(key.rstrip("s"))
            suffix = (" (default: ``%s``)" % default
                      if default is not None and text != default else "")
            lines.append(textwrap.fill(
                escape_rst(text) + suffix, width=76,
                initial_indent="    * **%s** — " % name,
                subsequent_indent="      "))
    if not command["documented"]:
        lines.append("")
        lines.append(textwrap.fill(
            "The syntax is derived from the interface declaration ``%s``; "
            "the header has no description for this command."
            % command["declaration"], width=76, initial_indent="    ",
            subsequent_indent="    "))
    if command["example"]:
        lines.append("")
        lines.append("    Example::")
        lines.append("")
        for example_line in command["example"].splitlines():
            lines.append("        " + example_line.rstrip())
    return "\n".join(lines)


def render(commands, title, intro, section_note):
    order = sorted(commands)
    groups = {}
    for name in order:
        groups.setdefault(name[0].upper(), []).append(name)

    lines = [
        ".. Generated by docs/make_command_reference.py from the .i files and",
        "   the header comments.  Do not edit by hand; run the script instead.",
        "",
        title,
        "=" * len(title),
        "",
    ]
    lines.extend(intro.strip().splitlines())
    lines.extend(["", section_note.strip(), ""])

    for letter in SECTION_LETTERS:
        names = groups.get(letter)
        if not names:
            continue
        lines.extend([letter, "-", ""])
        for name in names:
            lines.append(render_entry(commands[name]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


EN_INTRO = """\
Every command of the Tcl front end, in alphabetical order: the list is read
from the SWIG interface files under ``src``, and the syntax, description,
parameters and example come from the Doxygen comments in the headers.  The
Python package exposes the same names (``import surfit; surfit.area_read(...)``,
or the same call on a Session); the Python-only helpers -- ``Session``,
``values``, ``grid_auto``, ``add_surface``, ``progress``, ``viewer`` -- are
described in :doc:`python`.

The page is generated by ``docs/make_command_reference.py``; do not edit it by
hand."""

RU_INTRO = """\
Все команды Tcl-фронтенда в алфавитном порядке: список читается из
интерфейсных файлов SWIG в ``src``, а синтаксис, описание, параметры и пример
берутся из комментариев Doxygen в заголовках. Пакет Python даёт те же имена
(``import surfit; surfit.area_read(...)`` или тот же вызов у сессии);
только-Python помощники — ``Session``, ``values``, ``grid_auto``,
``add_surface``, ``progress``, ``viewer`` — описаны в :doc:`python`.

Описания команд приведены на английском: это исходные комментарии заголовков.
Страница генерируется ``docs/make_command_reference.py``; править её руками
не нужно."""

EN_NOTE = """\
Each entry gives the Tcl syntax, the description, the parameters and an example
when the header has one.""" 
RU_NOTE = """\
У каждой команды — синтаксис Tcl, описание, параметры и пример, если он есть в
заголовке."""


def main(argv):
    commands = interface_commands()
    docs = documented_blocks()
    for name, record in docs.items():
        if name not in commands:
            continue
        commands[name].update(record)
        commands[name]["documented"] = True

    for name, description in SUPPLEMENT.items():
        if name not in commands or commands[name]["documented"]:
            continue
        commands[name]["description"] = description
        commands[name]["documented"] = True

    en = render(commands, "Command reference", EN_INTRO, EN_NOTE)
    ru = render(commands, "Справочник команд", RU_INTRO, RU_NOTE)

    stale = []
    for path, content in ((EN, en), (RU, ru)):
        if "--check" in argv:
            current = ""
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as handle:
                    current = handle.read()
            if current != content:
                stale.append(path)
        else:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    documented = sum(1 for command in commands.values()
                     if command["documented"])
    print("%d command(s), %d with header documentation, %d without"
          % (len(commands), documented, len(commands) - documented))

    if "--check" in argv:
        for path in stale:
            print("stale: %s" % path)
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
