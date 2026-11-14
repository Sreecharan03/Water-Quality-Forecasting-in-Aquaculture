"""Split-conformal ranges from absolute errors: range = prediction +/- q, q = ceil((n+1)(1-alpha))-th smallest calibration error."""
from __future__ import annotations

import numpy as np


def conformal_q(abs_err: np.ndarray, alpha: float) -> float:
    a = np.asarray(abs_err, dtype=float)
    e = np.sort(a[~np.isnan(a)])
    n = len(e)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return float("inf") if k > n or n == 0 else float(e[k - 1])
