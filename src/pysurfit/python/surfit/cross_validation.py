"""Spatial cross-validation for a gridding workflow.

Random k-fold is optimistic when samples are clustered: neighbouring points
leak information between the training and validation sets.  This module makes
the fold geometry explicit and reports held-out error, not an uncertainty
model.  It does not solve anything itself; the caller supplies a ``build``
callback that returns a solved task or ``(values, extent)`` for one fold.

The default ``mode="random"`` is the cheap check.  Use ``mode="block"`` when
the samples have spatial structure: points are grouped into rectangular blocks,
and whole blocks are assigned to folds.  Choose the block size from the
variogram range when one is available; a block smaller than the range leaks.
"""

import numpy as np

from surfit import _surfit as _core
from surfit.diagnostics import point_residuals


def _points(x, y):
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if x.size != y.size:
        raise ValueError("x and y must have the same length")
    if x.size < 2:
        raise ValueError("cross-validation needs at least two points")
    return x, y


def _block_size(x, y, folds, block):
    if block is None:
        span = max(float(np.ptp(x)), float(np.ptp(y)))
        if span <= 0:
            raise ValueError("cannot infer a block size from zero extent")
        return span / np.sqrt(folds)
    if np.isscalar(block):
        size = float(block)
        return size, size
    block = tuple(float(value) for value in block)
    if len(block) != 2 or min(block) <= 0:
        raise ValueError("block must be a positive number or a (x, y) pair")
    return block


def fold_assignment(x, y, folds=4, mode="random", block=None, seed=0):
    """Return one fold label per point.

    ``mode="random"`` shuffles the point indices; ``mode="kfold"`` keeps the
    input order (useful when the caller already stratified the file);
    ``mode="block"`` groups points into rectangular blocks and assigns whole
    blocks to folds.  The returned labels are integers ``0 .. folds - 1``.
    """
    x, y = _points(x, y)
    if folds < 2:
        raise ValueError("folds must be at least 2")
    if folds > x.size:
        raise ValueError("folds cannot exceed the number of points")
    rng = np.random.default_rng(seed)

    if mode in ("random", "kfold"):
        order = rng.permutation(x.size) if mode == "random" else np.arange(x.size)
        labels = np.empty(x.size, dtype=int)
        labels[order] = np.arange(x.size) % folds
        return labels

    if mode != "block":
        raise ValueError("mode must be 'random', 'kfold' or 'block', not %r"
                         % (mode,))
    block_x, block_y = _block_size(x, y, folds, block)
    ix = np.floor((x - float(np.min(x))) / block_x).astype(int)
    iy = np.floor((y - float(np.min(y))) / block_y).astype(int)
    # A block id is unique in this extent; the fold assignment is per block,
    # so every point of a block is held out together.
    block_id = ix + iy * (int(ix.max()) + 1)
    ids = np.unique(block_id)
    if ids.size < folds:
        raise ValueError(
            "block size gives %d blocks for %d folds; use a smaller block"
            % (ids.size, folds))
    order = rng.permutation(ids.size)
    block_fold = {int(block_id_value): int(order[pos] % folds)
                  for pos, block_id_value in enumerate(ids)}
    return np.array([block_fold[int(value)] for value in block_id], dtype=int)


def _values_and_extent(result, extent):
    if isinstance(result, tuple):
        if len(result) != 2:
            raise TypeError("build() tuple must be (values, extent)")
        return np.asarray(result[0], dtype=float), result[1]
    if hasattr(result, "values") and callable(result.values):
        values = np.asarray(result.values(), dtype=float)
        position = int(result.surf_count()) - 1
        if position < 0:
            raise ValueError("build() returned a task without a surface")
        return values, _core.surf_extent(position)
    if extent is None:
        raise TypeError(
            "build() must return a task, (values, extent), or an array with "
            "the extent= argument set")
    return np.asarray(result, dtype=float), extent


def _metrics(residuals, weights):
    residuals = np.asarray(residuals, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if residuals.size == 0:
        return {"n": 0, "rmse": float("nan"), "bias": float("nan"),
                "mae": float("nan"), "weighted_mse": float("nan")}
    weight_sum = float(weights.sum())
    return {
        "n": int(residuals.size),
        "rmse": float(np.sqrt(np.mean(residuals * residuals))),
        "bias": float(np.mean(residuals)),
        "mae": float(np.mean(np.abs(residuals))),
        "weighted_mse": float(np.sum(weights * residuals * residuals)
                              / weight_sum),
    }


def cross_validate(build, x, y, z, weights=None, folds=4, mode="random",
                   block=None, seed=0, extent=None):
    """Run spatial cross-validation and return held-out summary metrics.

    ``build(train_indices, train_weights)`` must return a solved task,
    ``(values, extent)``, or an array when ``extent`` is given.  ``train_weights``
    is ``None`` when no weights were supplied.  The callback must build a model
    from that fold's training points only; the validation points are never
    passed to it.

    The result is JSON-ready: per-fold RMSE, bias, MAE and weighted MSE, plus
    the same metrics over all held-out points.  These are point errors under
    the fold design, not a posterior or a map of uncertainty.
    """
    x, y = _points(x, y)
    z = np.asarray(z, dtype=float).ravel()
    if z.size != x.size:
        raise ValueError("z must have one value per point")
    has_weights = weights is not None
    if not has_weights:
        weights = np.ones(x.size, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float).ravel()
        if weights.size != x.size:
            raise ValueError("weights must have one value per point")

    labels = fold_assignment(x, y, folds=folds, mode=mode, block=block,
                             seed=seed)
    fold_details = []
    all_residuals = []
    all_weights = []
    for number in range(folds):
        train = np.flatnonzero(labels != number)
        test = np.flatnonzero(labels == number)
        if train.size == 0 or test.size == 0:
            raise ValueError(
                "fold %d is empty; use a smaller block or more blocks"
                % number)
        train_weights = weights[train] if has_weights else None
        result = build(train, train_weights)
        values, result_extent = _values_and_extent(result, extent)
        stats = point_residuals(values, result_extent, x[test], y[test],
                                z[test], weights[test])
        used_weights = weights[test][stats["used"]]
        all_residuals.append(stats["residuals"])
        all_weights.append(used_weights)
        details = _metrics(stats["residuals"], used_weights)
        details.update({"fold": number, "n_train": int(train.size),
                        "n_test": int(test.size)})
        fold_details.append(details)

    residuals = np.concatenate(all_residuals) if all_residuals else np.array([])
    used_weights = np.concatenate(all_weights) if all_weights else np.array([])
    overall = _metrics(residuals, used_weights)
    overall.update({"folds": folds, "mode": mode,
                    "block": list(block) if isinstance(block, tuple) else block,
                    "fold_details": fold_details})
    return overall
