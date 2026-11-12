"""Standalone geometric V-cycle prototype for the 2D Poisson operator.

The surfit CMOFS matrix is not exposed as a grid hierarchy, so this module is a
numerical baseline rather than an integrated solver.  It uses a cell-centred
5-point Laplacian, bilinear interpolation, Galerkin coarse operators and
red-black Gauss-Seidel smoothing.
"""

import numpy as np


def _laplacian(n):
    diagonal = np.diag(np.full(n, 2.0))
    off = np.diag(np.full(n - 1, -1.0), 1)
    one_d = diagonal + off + off.T
    return np.kron(np.eye(n), one_d) + np.kron(one_d, np.eye(n))


def _interpolation(n):
    coarse = n // 2
    matrix = np.zeros((n, coarse))
    for index in range(n):
        position = (index + 0.5) / n * coarse - 0.5
        left = int(np.floor(position))
        weight = position - left
        if left < 0:
            left, weight = 0, 0.0
        if left >= coarse - 1:
            left, weight = coarse - 2, 1.0
        matrix[index, left] = 1.0 - weight
        matrix[index, left + 1] = weight
    return matrix


def _smooth(u, b, n, iterations=2):
    for _ in range(iterations):
        for color in (0, 1):
            for i in range(n):
                for j in range(n):
                    if (i + j) % 2 != color:
                        continue
                    value = b[i * n + j]
                    if i > 0:
                        value += u[(i - 1) * n + j]
                    if i + 1 < n:
                        value += u[(i + 1) * n + j]
                    if j > 0:
                        value += u[i * n + j - 1]
                    if j + 1 < n:
                        value += u[i * n + j + 1]
                    u[i * n + j] = value / 4.0


def _vcycle(matrix, b, n, u):
    _smooth(u, b, n)
    residual = b - matrix @ u
    if n <= 4:
        return np.linalg.solve(matrix, b)
    one_d = _interpolation(n)
    prolong = np.kron(one_d, one_d)
    coarse_matrix = prolong.T @ matrix @ prolong
    coarse = _vcycle(coarse_matrix, prolong.T @ residual, n // 2,
                     np.zeros(n * n // 4))
    u = u + prolong @ coarse
    _smooth(u, b, n)
    return u


def poisson_vcycle(n=64, cycles=6):
    """Run V-cycles on a cell-centred Poisson problem and return residuals."""
    if n < 8 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two, at least 8")
    matrix = _laplacian(n)
    rhs = np.ones(n * n)
    values = np.zeros(n * n)
    residuals = []
    for _ in range(cycles):
        values = _vcycle(matrix, rhs, n, values)
        residuals.append(float(np.linalg.norm(rhs - matrix @ values)))
    return {"residuals": residuals, "values": values.reshape(n, n)}
