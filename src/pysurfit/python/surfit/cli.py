"""Command-line entry point for recipes: ``surfit run recipe.json``."""

import argparse
import json
import sys

import numpy as np

import surfit
from surfit.recipe import recipe_summary, run_recipe


def _result_document(task, recipe):
    grid = np.asarray(task.values(), dtype=float)
    defined = surfit.defined_mask(grid)
    finite = grid[defined]
    document = {
        "ok": True,
        "name": recipe_summary(recipe)["name"],
        "shape": [int(grid.shape[0]), int(grid.shape[1])],
        "defined": int(defined.sum()),
        "undefined": int(grid.size - defined.sum()),
        "min": float(finite.min()) if finite.size else None,
        "max": float(finite.max()) if finite.size else None,
        "mean": float(finite.mean()) if finite.size else None,
    }
    return document


def _write_json(path, document):
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2)


def _execute(args):
    try:
        task = run_recipe(args.recipe)
    except Exception as error:
        if args.result_json:
            _write_json(args.result_json, {"ok": False, "error": str(error)})
        print("surfit: %s" % error, file=sys.stderr)
        return 1
    try:
        if args.result_json:
            _write_json(args.result_json, _result_document(task, args.recipe))
    except Exception as error:
        print("surfit: %s" % error, file=sys.stderr)
        return 1
    finally:
        task.close()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="surfit")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a JSON/YAML recipe")
    run.add_argument("recipe")
    run.add_argument("--summary", action="store_true",
                     help="print the recipe summary without solving")
    run.add_argument("--json", action="store_true",
                     help="print the summary as JSON")
    run.add_argument("--result-json",
                     help="write a machine-readable result document")
    args = parser.parse_args(argv)
    if args.command != "run":
        parser.error("unknown command")
    if args.summary:
        summary = recipe_summary(args.recipe)
        print(json.dumps(summary, indent=2) if args.json
              else json.dumps(summary))
        return 0
    return _execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
