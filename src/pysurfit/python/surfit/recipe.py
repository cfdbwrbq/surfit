"""Declarative task recipes and a small runner.

A recipe is JSON (or YAML when PyYAML is installed).  It describes one Session:
grid, data, ordered rules and output.  The runner is intentionally thin: every
rule is still a normal Session call, so the recipe cannot bypass validation.
"""

import json
import os


def _load(path):
    suffix = os.path.splitext(path)[1].lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as error:
            raise ImportError("YAML recipes need PyYAML") from error
        with open(path, encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def _resolve(base, path):
    if path is None or os.path.isabs(path):
        return path
    return os.path.join(base, path)


def _add_data(task, item, base):
    kind = item.get("kind")
    name = item.get("name")
    path = _resolve(base, item.get("path"))
    if kind == "points":
        task.read_points(path, name, **item.get("options", {}))
    elif kind == "curves":
        task.read_curves(path, name)
    elif kind == "areas":
        task.read_areas(path, name)
    elif kind == "contours":
        task.read_contours(path, name)
    elif kind == "surface":
        import numpy as np

        values = np.load(path, allow_pickle=False)
        extent = item["extent"]
        task.add_surface(values, extent["min_x"], extent["step_x"],
                         extent["min_y"], extent["step_y"], name)
    else:
        raise ValueError("unknown recipe data kind %r" % (kind,))


def run_recipe(recipe, base_dir=None):
    """Execute a recipe mapping or a path to a JSON/YAML recipe."""
    from surfit import Session

    if isinstance(recipe, str):
        base_dir = os.path.dirname(os.path.abspath(recipe))
        recipe = _load(recipe)
    elif base_dir is None:
        base_dir = os.getcwd()
    if not isinstance(recipe, dict):
        raise TypeError("recipe must be a mapping")
    task = Session(map_name=recipe.get("name", "recipe"),
                   tol=recipe.get("tol"), strict=recipe.get("strict", False))
    try:
        grid = recipe.get("grid")
        if grid is None:
            grid = recipe.get("grid_args")
        if grid is None:
            raise ValueError("recipe needs a 'grid' or 'grid_args'")
        task.grid(*grid)
        for item in recipe.get("data", []):
            _add_data(task, item, base_dir)
        for rule in recipe.get("rules", []):
            if isinstance(rule, str):
                command, args, kwargs = rule, [], {}
            else:
                command = rule.get("command")
                args = rule.get("args", [])
                kwargs = rule.get("kwargs", {})
            if not command:
                raise ValueError("recipe rule needs a command")
            getattr(task, command)(*args, **kwargs)
        task.solve()
        output = recipe.get("output", {})
        if output.get("save"):
            task.save(_resolve(base_dir, output["save"]))
        if output.get("metadata"):
            task.save_metadata(_resolve(base_dir, output["metadata"]))
        return task
    except Exception:
        task.close()
        raise


def recipe_summary(recipe):
    """Small JSON-ready description without solving."""
    if isinstance(recipe, str):
        recipe = _load(recipe)
    return {
        "name": recipe.get("name", "recipe"),
        "grid": recipe.get("grid") or recipe.get("grid_args"),
        "data": [item.get("kind") for item in recipe.get("data", [])],
        "rules": [rule if isinstance(rule, str) else rule.get("command")
                  for rule in recipe.get("rules", [])],
    }
