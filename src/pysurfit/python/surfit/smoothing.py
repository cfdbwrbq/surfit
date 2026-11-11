"""Select a smoothing/regularisation parameter with spatial CV.

The engine's point weight, completer weights and tolerance are usually chosen
by hand.  This helper runs the same spatial CV for each candidate and returns
the best score; it does not change the solver or claim an optimal model.
"""

import numpy as np

from surfit.cross_validation import cross_validate


def select_parameter(build, x, y, z, parameters, weights=None, folds=4,
                     mode="block", block=None, seed=0, metric="rmse",
                     groups=None):
    """Run spatial CV for each candidate and return the best parameter.

    ``build(parameter, train_indices, train_weights)`` must return a solved
    task, ``(values, extent)`` or an array with ``extent=``.  The returned
    ``scores`` table is JSON-ready; the selection metric is ``rmse``.
    """
    parameters = list(parameters)
    if not parameters:
        raise ValueError("parameters must not be empty")
    if metric != "rmse":
        raise ValueError("only metric='rmse' is supported")
    scores = []
    for parameter in parameters:
        def builder(train, train_weights, parameter=parameter):
            return build(parameter, train, train_weights)

        result = cross_validate(
            builder, x, y, z, weights=weights, folds=folds, mode=mode,
            block=block, seed=seed, groups=groups)
        scores.append({
            "parameter": parameter,
            "rmse": result["rmse"],
            "bias": result["bias"],
            "mae": result["mae"],
            "n": result["n"],
        })
    best = min(scores, key=lambda item: item[metric])
    return {
        "parameter": best["parameter"],
        "metric": metric,
        "score": best[metric],
        "scores": scores,
    }
