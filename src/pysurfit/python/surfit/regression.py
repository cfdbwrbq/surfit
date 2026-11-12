"""Trend + residual wrapper around a scikit-learn-compatible regressor.

The wrapper does not change the solver: it fits a trend to covariates, returns
observed minus trend, and leaves the residual interpolation to surfit.  The
default model is ordinary least squares with an intercept, so the helper works
without scikit-learn.
"""

import numpy as np


def _design(features, intercept):
    features = np.asarray(features, dtype=float)
    if features.ndim != 2:
        raise ValueError("features must be a 2D array")
    if intercept:
        return np.column_stack((np.ones(features.shape[0]), features))
    return features


def regression_trend(features, values, model=None, intercept=True):
    """Fit a trend and return trend, residuals and fit statistics.

    ``model`` must implement ``fit`` and ``predict``; when omitted, ordinary
    least squares with an intercept is used.  Rows with non-finite values are
    excluded from fitting and their trend/residual is NaN.
    """
    features = np.asarray(features, dtype=float)
    values = np.asarray(values, dtype=float).ravel()
    if features.ndim != 2:
        raise ValueError("features must be a 2D array")
    if features.shape[0] != values.size:
        raise ValueError("features and values must have the same row count")
    valid = np.isfinite(values) & np.all(np.isfinite(features), axis=1)
    if valid.sum() < 2:
        raise ValueError("at least two finite rows are required")
    trend = np.full(values.shape, np.nan, dtype=float)
    if model is None:
        design = _design(features[valid], intercept)
        coefficients, _, _, _ = np.linalg.lstsq(design, values[valid],
                                                rcond=None)
        trend[valid] = _design(features[valid], intercept) @ coefficients
        fitted = {"kind": "ols", "coefficients": coefficients}
    else:
        if not hasattr(model, "fit") or not hasattr(model, "predict"):
            raise TypeError("model must implement fit() and predict()")
        fitted_model = model.fit(features[valid], values[valid])
        trend[valid] = np.asarray(fitted_model.predict(features[valid]))
        fitted = {"kind": type(model).__name__, "model": fitted_model}
    residuals = values - trend
    finite = np.isfinite(residuals)
    return {
        "trend": trend,
        "residuals": residuals,
        "fit": fitted,
        "n": int(valid.sum()),
        "rmse": float(np.sqrt(np.mean(residuals[finite] ** 2))),
        "bias": float(np.mean(residuals[finite])),
    }


def add_regression_residuals(task, x, y, z, features, model=None,
                             name="regression_residuals"):
    """Fit a trend and register the residual points in a Session."""
    result = regression_trend(features, z, model=model)
    task.add_points(x, y, result["residuals"], name=name)
    return result
