"""Place probabilities from win probabilities (Harville)."""

from __future__ import annotations

import numpy as np


def harville_place_probs(win_p: np.ndarray, n_places: int) -> np.ndarray:
    """P(finish in the top n_places) from win probabilities that sum to 1."""
    p = np.asarray(win_p, dtype=float)
    p = np.clip(p, 1e-12, None)
    total = p.sum()
    if total <= 0:
        return np.full(len(p), np.nan)
    p = p / total
    n = len(p)
    k = int(max(0, min(n_places, n)))
    if k <= 0:
        return np.zeros(n)
    if k == 1:
        return p.copy()
    if k >= n:
        return np.ones(n)

    place = p.copy()
    for i in range(n):
        second = 0.0
        for j in range(n):
            if i == j:
                continue
            denom = 1.0 - p[j]
            if denom <= 1e-12:
                continue
            second += p[j] * p[i] / denom
        place[i] += second
    if k == 2:
        return np.clip(place, 0.0, 1.0)

    for i in range(n):
        third = 0.0
        for j in range(n):
            if j == i:
                continue
            for m in range(n):
                if m == i or m == j:
                    continue
                d1 = 1.0 - p[j]
                d2 = 1.0 - p[j] - p[m]
                if d1 <= 1e-12 or d2 <= 1e-12:
                    continue
                third += p[j] * (p[m] / d1) * (p[i] / d2)
        place[i] += third
    return np.clip(place, 0.0, 1.0)
