import numpy as np
from scipy.linalg import cho_factor, cho_solve, LinAlgError, pinvh
from scipy.stats import chi2

def mahalanobis_distance(x, xhat, R, *, squared: bool = False) -> float:
    """
    Compute Mahalanobis distance between x and xhat under covariance R.

    Parameters
    ----------
    x : array_like, shape (n,) or (n,1)
        Measurement (or sample) vector.
    xhat : array_like, shape (n,) or (n,1)
        Predicted/mean vector to compare against.
    R : array_like, shape (n,n)
        Covariance (e.g., measurement noise). Must be symmetric PSD/PD.
    squared : bool, default False
        If True, return the squared distance (y^T R^{-1} y).

    Returns
    -------
    float
        Mahalanobis distance (or squared distance if squared=True).
    """
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    xhat = np.asarray(xhat, dtype=float).reshape(-1, 1)
    R = np.asarray(R, dtype=float)  # pyright: ignore[reportConstantRedefinition]

    if x.shape != xhat.shape:
        raise ValueError(f"Shape mismatch: x {x.shape} vs xhat {xhat.shape}")
    n = x.shape[0]
    if R.shape != (n, n):
        raise ValueError(f"R must be {(n, n)}, got {R.shape}")

    y = x - xhat  # innovation

    # Try Cholesky-based solve (stable for PD matrices)
    try:
        c, lower = cho_factor(R, check_finite=False)
        v = cho_solve((c, lower), y, check_finite=False)  # v = R^{-1} y
        d2 = float(y.T @ v)  # y^T R^{-1} y
    except LinAlgError:
        # Fall back to pseudo-inverse for semi-definite / near-singular R
        R_pinv = pinvh(R, check_finite=False)
        d2 = float(y.T @ (R_pinv @ y))

    return d2 if squared else float(np.sqrt(d2))

def percent_confidence(distance_squared: float, measurement_dim: int) -> float:
    p_value = 1 - chi2.cdf(distance_squared, df=measurement_dim)
    return float(p_value) * 100.0