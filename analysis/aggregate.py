"""Equal-game aggregates, within-game percentile bootstrap and BCa intervals."""

import warnings
from collections import defaultdict

import numpy as np
from scipy.stats import bootstrap

from .scoring import GAMES


def aggregate(episodes, *, resamples=10000, seed=42):
    if resamples < 1:
        raise ValueError("resamples must be positive")
    grouped = defaultdict(list)
    for e in episodes:
        grouped[(e["model"], e["mode"], e["language"], e["game"])].append(e)
    rng = np.random.default_rng(seed)
    rows, distributions = [], {}
    for key, items in sorted(grouped.items()):
        values = np.array([[e["score"], float(e["won"])] for e in items])
        draws = np.empty((resamples, 2))
        # Bounded batches also support larger custom datasets.
        for start in range(0, resamples, 1000):
            stop = min(start + 1000, resamples)
            draws[start:stop] = values[
                rng.integers(0, len(values), (stop - start, len(values)))
            ].mean(axis=1)
        distributions[key] = draws
        low, high = np.quantile(draws, [0.025, 0.975], axis=0)
        rows.append(
            dict(zip(("model", "mode", "language", "game"), key))
            | {
                "n": len(items),
                "score": float(values[:, 0].mean()),
                "score_ci_low": float(low[0]),
                "score_ci_high": float(high[0]),
                "win_rate": float(values[:, 1].mean()),
                "win_rate_ci_low": float(low[1]),
                "win_rate_ci_high": float(high[1]),
            }
        )
    for model, mode, language in sorted({key[:3] for key in grouped}):
        selected = [
            row
            for row in rows
            if (row["model"], row["mode"], row["language"]) == (model, mode, language)
        ]
        if {row["game"] for row in selected} != set(GAMES):
            raise ValueError(
                f"Cannot compute Total with missing games: {model}, {mode}, {language}"
            )
        draws = np.mean(
            [distributions[(model, mode, language, g)] for g in GAMES], axis=0
        )
        low, high = np.quantile(draws, [0.025, 0.975], axis=0)
        rows.append(
            {
                "model": model,
                "mode": mode,
                "language": language,
                "game": "Total",
                "n": sum(row["n"] for row in selected),
                "score": float(np.mean([row["score"] for row in selected])),
                "score_ci_low": float(low[0]),
                "score_ci_high": float(high[0]),
                "win_rate": float(np.mean([row["win_rate"] for row in selected])),
                "win_rate_ci_low": float(low[1]),
                "win_rate_ci_high": float(high[1]),
            }
        )
    return rows


def bca_mean_ci(values, *, resamples=10000, seed=42):
    """Mean and 95% BCa interval, as in the paper's per-cell figure bands.

    Constant or single-value samples have a degenerate interval; BCa warnings
    fall back to the percentile interval of the same resamples' generator.
    """
    data = np.asarray(values, dtype=float)
    mean = float(np.mean(data))
    if len(data) < 2 or np.allclose(data, data[0]):
        return mean, mean, mean
    rng = np.random.default_rng(seed)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            interval = bootstrap(
                (data,), np.mean, n_resamples=resamples, method="BCa", random_state=rng
            ).confidence_interval
        return mean, float(interval.low), float(interval.high)
    except Exception:
        draws = rng.integers(0, len(data), (resamples, len(data)))
        means = np.array([np.mean(data[i]) for i in draws])
        return mean, float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
