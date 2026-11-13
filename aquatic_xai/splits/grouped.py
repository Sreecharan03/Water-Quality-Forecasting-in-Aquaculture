"""Pond-level (group) assignment: sealed unseen-pond test ponds and grouped CV folds. Deterministic."""
from __future__ import annotations

import numpy as np


def pick_sealed(eligible: list[str], n: int, seed: int) -> list[str]:
    pool = sorted(eligible)
    if len(pool) < n:
        raise ValueError(f"only {len(pool)} eligible ponds for {n} sealed slots")
    rng = np.random.RandomState(seed)
    return sorted(pool[i] for i in rng.choice(len(pool), size=n, replace=False))


def assign_folds(val_counts: dict[str, int], k: int, min_origins: int) -> dict[str, int]:
    """Greedy balance of held-out validation origins across k folds. Ponds below the minimum get -1
    (always used for training, never held out)."""
    folds = {p: -1 for p in val_counts}
    eligible = sorted((p for p, c in val_counts.items() if c >= min_origins), key=lambda p: (-val_counts[p], p))
    load = [0] * k
    for p in eligible:
        f = int(np.argmin(load))
        folds[p] = f
        load[f] += val_counts[p]
    return folds
