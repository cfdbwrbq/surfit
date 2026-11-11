"""Variogram diagnostics for point data.

The solver's ``completer`` takes an anisotropy angle and factor, but the user
had to guess them.  These helpers estimate an experimental semivariogram, fit a
simple model and suggest an anisotropy direction/ratio.  They do not add
kriging or a covariance matrix to the engine; the result is a diagnostic and a
set of starting values for the existing rules.

Distances are in the data's coordinate units.  Direction 0 is +x, 90 is +y.
A direction selects pairs whose separation is within ``tolerance`` degrees of
that line; an unoriented pair (angle + 180) is equivalent.
"""

import numpy as np

_MODELS = ("spherical", "exponential", "gaussian")


def _pairs(x, y, z, max_lag):
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    z = np.asarray(z, dtype=float).ravel()
    if not (x.size == y.size == z.size):
        raise ValueError("x, y and z must have the same length")
    if x.size < 2:
        raise ValueError("a variogram needs at least two points")
    dx = []
    dy = []
    dz = []
    for first in range(x.size - 1):
        distance_x = x[first + 1:] - x[first]
        distance_y = y[first + 1:] - y[first]
        distance = np.hypot(distance_x, distance_y)
        keep = np.isfinite(distance) & (distance > 0)
        if max_lag is not None:
            keep &= distance <= float(max_lag)
        dx.append(distance_x[keep])
        dy.append(distance_y[keep])
        dz.append(z[first + 1:][keep] - z[first])
    return (np.concatenate(dx), np.concatenate(dy),
            np.concatenate(dz))


def _bin_edges(distances, bins, max_lag):
    if max_lag is None:
        max_lag = float(np.max(distances))
    if max_lag <= 0:
        raise ValueError("max_lag must be positive")
    return np.linspace(0.0, float(max_lag), int(bins) + 1), float(max_lag)


def experimental_variogram(x, y, z, bins=20, max_lag=None, direction=None,
                           tolerance=22.5, estimator="classical"):
    """Experimental semivariogram with optional directional selection.

    ``estimator="classical"`` uses half the mean squared difference;
    ``"robust"`` uses the Cressie-Hawkins fourth-root estimator, which is less
    sensitive to a few large differences.  Returns lag centres, gamma, pair
    counts and the parameters used.
    """
    if estimator not in ("classical", "robust"):
        raise ValueError("estimator must be 'classical' or 'robust'")
    dx, dy, dz = _pairs(x, y, z, max_lag)
    distance = np.hypot(dx, dy)
    if direction is not None:
        angle = np.degrees(np.arctan2(dy, dx)) % 180.0
        target = float(direction) % 180.0
        difference = np.abs(angle - target)
        difference = np.minimum(difference, 180.0 - difference)
        keep = difference <= float(tolerance)
        distance = distance[keep]
        dz = dz[keep]
    if distance.size == 0:
        raise ValueError("no point pairs satisfy the direction/tolerance")
    edges, limit = _bin_edges(distance, bins, max_lag)
    index = np.digitize(distance, edges) - 1
    index = np.clip(index, 0, len(edges) - 2)
    centers = (edges[:-1] + edges[1:]) / 2.0
    gamma = []
    counts = []
    for number in range(len(centers)):
        values = dz[index == number]
        counts.append(int(values.size))
        if values.size == 0:
            gamma.append(np.nan)
        elif estimator == "classical":
            gamma.append(float(0.5 * np.mean(values * values)))
        else:
            root = np.mean(np.abs(values) ** 0.5)
            gamma.append(float(root ** 4 / (0.457 + 0.494 / values.size)))
    return {
        "lag": centers,
        "gamma": np.asarray(gamma, dtype=float),
        "count": np.asarray(counts, dtype=int),
        "direction": direction,
        "tolerance": tolerance,
        "estimator": estimator,
        "max_lag": limit,
    }


def _correlation(model, lag, range_):
    ratio = np.asarray(lag, dtype=float) / max(float(range_), 1e-12)
    if model == "spherical":
        return np.where(ratio < 1.0,
                        1.0 - 1.5 * ratio + 0.5 * ratio ** 3, 0.0)
    if model == "exponential":
        return np.exp(-3.0 * ratio)
    return np.exp(-3.0 * ratio * ratio)


def fit_variogram(lag, gamma, model="spherical", range_=None):
    """Fit ``nugget + partial_sill * correlation(h)`` to a variogram.

    The range is searched on a grid; nugget and sill are non-negative least
    squares for each trial range.  Returns the model parameters, fitted values
    and RMSE.  This is a diagnostic fit, not a maximum-likelihood estimate.
    """
    lag = np.asarray(lag, dtype=float).ravel()
    gamma = np.asarray(gamma, dtype=float).ravel()
    if lag.size != gamma.size:
        raise ValueError("lag and gamma must have the same length")
    keep = np.isfinite(lag) & np.isfinite(gamma) & (lag > 0)
    lag = lag[keep]
    gamma = gamma[keep]
    if gamma.size < 3:
        raise ValueError("at least three finite variogram bins are needed")
    if model not in _MODELS:
        raise ValueError("model must be one of %s" % ", ".join(_MODELS))
    if range_ is None:
        low = max(float(lag.min()) * 0.25, 1e-12)
        high = max(float(lag.max()) * 1.5, low * 2.0)
        ranges = np.linspace(low, high, 80)
    else:
        ranges = np.asarray([float(range_)], dtype=float)
    best = None
    for candidate in ranges:
        correlation = _correlation(model, lag, candidate)
        design = np.column_stack((np.ones_like(correlation), correlation))
        coefficients = np.linalg.lstsq(design, gamma, rcond=None)[0]
        coefficients = np.maximum(coefficients, 0.0)
        fitted = design @ coefficients
        error = float(np.sqrt(np.mean((fitted - gamma) ** 2)))
        if best is None or error < best[0]:
            best = (error, candidate, coefficients[0], coefficients[1], fitted)
    error, candidate, nugget, sill, fitted = best
    if sill <= 0:
        sill = float(np.var(gamma)) or 1.0
    return {
        "model": model,
        "range": float(candidate),
        "nugget": float(nugget),
        "sill": float(sill),
        "total_sill": float(nugget + sill),
        "rmse": float(error),
        "lags": lag.tolist(),
        "gamma": gamma.tolist(),
        "fitted": fitted.tolist(),
    }


def anisotropy(x, y, z, angles=(0.0, 45.0, 90.0, 135.0), bins=12,
               max_lag=None, tolerance=22.5, model="spherical", strict=False):
    """Suggest an anisotropy angle and ratio from directional variograms.

    Returns ``angle`` (degrees), ``ratio`` (long range / short range) and a
    per-direction range table.  This is a coarse diagnostic: use it to seed
    ``completer(..., alpha=angle, w=ratio)``, not as a fitted covariance model.
    """
    angles = tuple(float(value) for value in angles)
    if len(angles) < 2:
        raise ValueError("anisotropy needs at least two directions")
    fits = []
    skipped = []
    for direction in angles:
        try:
            experimental = experimental_variogram(
                x, y, z, bins=bins, max_lag=max_lag, direction=direction,
                tolerance=tolerance)
            fit = fit_variogram(experimental["lag"], experimental["gamma"],
                                model=model)
        except ValueError as error:
            skipped.append({"direction": direction, "reason": str(error)})
            continue
        fits.append({"direction": direction, "range": fit["range"],
                     "sill": fit["total_sill"], "rmse": fit["rmse"],
                     "bins": int(np.sum(experimental["count"] > 0))})
    if skipped and strict:
        raise ValueError(
            "anisotropy skipped directions: %s" % skipped)
    if len(fits) < 2:
        raise ValueError(
            "not enough directions have usable variograms: %s" % skipped)
    longest = max(fits, key=lambda item: item["range"])
    shortest = min(fits, key=lambda item: item["range"])
    ratio = longest["range"] / max(shortest["range"], 1e-12)
    return {
        "angle": longest["direction"],
        "ratio": float(ratio),
        "ranges": fits,
        "skipped": skipped,
        "model": model,
    }
