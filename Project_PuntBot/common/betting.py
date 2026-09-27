"""Commission, P&L, and probability scores used by every sport."""

from __future__ import annotations

import numpy as np
import pandas as pd

COMMISSION = 0.06


def break_even_probability(odds: float, commission: float = COMMISSION) -> float:
    net_odds = 1.0 + (odds - 1.0) * (1.0 - commission)
    return 1.0 / net_odds


def back_profit(won: bool, odds: float, stake: float, commission: float = COMMISSION) -> float:
    if won:
        return (odds - 1.0) * (1.0 - commission) * stake
    return -stake


def lay_profit(won: bool, odds: float, liability: float = 1.0, commission: float = COMMISSION) -> float:
    """Unit-liability lay: risk $1 if the selection wins."""
    if odds <= 1.0:
        return 0.0
    if won:
        return -liability
    return liability / (odds - 1.0) * (1.0 - commission)


def brier_score(prob: pd.Series | np.ndarray, won: pd.Series | np.ndarray) -> float:
    p = np.asarray(prob, dtype=float)
    y = np.asarray(won, dtype=float)
    return float(np.mean((p - y) ** 2))
