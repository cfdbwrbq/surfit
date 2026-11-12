"""Command-line entry point for recipes: ``surfit run recipe.json``."""

import argparse
import json

from surfit.recipe import recipe_summary, run_recipe


def main(argv=None):
    parser = argparse.ArgumentParser(prog="surfit")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a JSON/YAML recipe")
    run.add_argument("recipe")
    run.add_argument("--summary", action="store_true",
                     help="print the recipe summary without solving")
    run.add_argument("--json", action="store_true",
                     help="print the summary as JSON")
    args = parser.parse_args(argv)
    if args.command != "run":
        parser.error("unknown command")
    if args.summary:
        summary = recipe_summary(args.recipe)
        print(json.dumps(summary, indent=2) if args.json
              else json.dumps(summary))
        return 0
    task = run_recipe(args.recipe)
    task.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
