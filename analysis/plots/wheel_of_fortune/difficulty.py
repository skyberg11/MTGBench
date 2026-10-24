"""Russian Wheel of Fortune scores by Easy/Medium/Hard target complexity."""

import csv
import json
import textwrap
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dataset_generation.wheel_of_fortune.generate import calculate_word_difficulty

from ...aggregate import bca_mean_ci
from ..wordle import save

# Main-text configurations in legend order; each model keeps one Okabe-Ito colour.
SELECTED = (
    ("deepseek-v4-pro", "DeepSeek V4 Pro", "#0072B2"),
    ("gpt-5.4", "GPT 5.4", "#009E73"),
    ("gpt-5.4-mini", "GPT 5.4 Mini", "#E69F00"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview", "#56B4E9"),
    ("qwen3-235b-a22b-thinking-2507", "Qwen3 235B A22B Thinking 2507", "#F0E442"),
    ("qwen3.5-35b-a3b", "Qwen3.5 35B A3B", "#D55E00"),
)
MODES = (
    ("reasoning", "Reason", "dashdot"),
    ("cot", "CoT", "dashdot"),
    ("answer_only", "AO", "solid"),
)
BUCKETS = ("Easy", "Medium", "Hard")


def bucket_of(target, thresholds):
    """Equal-size terciles of the letter-rarity score used to build the dataset."""
    score = calculate_word_difficulty(target, "ru")
    return BUCKETS[(score > thresholds[0]) + (score > thresholds[1])]


def collect_cells(episodes, root, resamples, seed):
    words = json.loads(
        (
            root
            / "multiturn_games_benchmark/datasets/wheel_of_fortune/ru_letter_difficulty_words.json"
        ).read_text(encoding="utf-8")
    )["words"]
    scores = sorted(w["difficulty_score"] for w in words)
    thresholds = (scores[len(scores) // 3], scores[2 * len(scores) // 3])
    grouped = defaultdict(list)
    for e in episodes:
        if e["game"] == "wheel_of_fortune" and e["language"] == "ru":
            grouped[(e["model"], e["mode"], bucket_of(e["target"], thresholds))].append(
                e["score"]
            )
    rows = []
    # Export every LLM for the site's model selector; the paper plot keeps SELECTED.
    for model in sorted({model for model, _, _ in grouped if model != "human"}):
        for mode, mode_label, _ in MODES:
            for bucket in BUCKETS:
                values = grouped.get((model, mode, bucket))
                if values:
                    mean, low, high = bca_mean_ci(
                        values, resamples=resamples, seed=seed
                    )
                    rows.append(
                        {
                            "model": model,
                            "mode": mode,
                            "bucket": bucket,
                            "n": len(values),
                            "score": mean,
                            "score_ci_low": low,
                            "score_ci_high": high,
                        }
                    )
    return rows


def plot_difficulty(episodes, root, output, resamples=10000, seed=42):
    rows = collect_cells(episodes, root, resamples, seed)
    name = "wheel_of_fortune_per_level_speed_trend_3bin_ru"
    directory = output / "tables"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    for model, label, color in SELECTED:
        for mode, mode_label, style in MODES:
            cells = [r for r in rows if (r["model"], r["mode"]) == (model, mode)]
            if not cells:
                continue
            xs = [BUCKETS.index(r["bucket"]) for r in cells]
            ax.plot(
                xs,
                [r["score"] for r in cells],
                linestyle=style,
                color=color,
                linewidth=2.0,
                marker="o",
                markersize=5,
                alpha=0.95,
                zorder=2,
                label=f"{label} ({mode_label})",
            )
            ax.fill_between(
                xs,
                [r["score_ci_low"] for r in cells],
                [r["score_ci_high"] for r in cells],
                color=color,
                alpha=0.12,
            )
    selected_models = {model for model, _, _ in SELECTED}
    plotted_rows = [row for row in rows if row["model"] in selected_models]
    low = min(r["score_ci_low"] for r in plotted_rows)
    high = max(r["score_ci_high"] for r in plotted_rows)
    ax.set_ylim(max(0.0, low - 0.05), min(1.02, high + 0.05))
    ax.set_xticks(range(len(BUCKETS)), BUCKETS, fontsize=14)
    ax.tick_params(axis="y", labelsize=13)
    ax.set_xlabel("Difficulty level", fontsize=15, fontweight="bold")
    ax.set_ylabel(
        "Performance score\n(BCa 95% CI band)", fontsize=15, fontweight="bold"
    )
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles,
        [
            textwrap.fill(l, width=20, break_long_words=False, break_on_hyphens=False)
            for l in labels
        ],
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=13,
        frameon=False,
    )
    # The paper's layout reserved a title that its PDF then left blank; reserving
    # it here too and cropping reproduces the figure's size and aspect.
    ax.set_title(
        "Wheel of Fortune performance —\nEasy/Medium/Hard (RU)",
        fontsize=16,
        fontweight="bold",
    )
    fig.tight_layout()
    ax.set_title("")
    # TrueType fonts, as in the paper: ACL's checker rejects the default Type 3.
    with matplotlib.rc_context({"pdf.fonttype": 42}):
        save(fig, output, name, bbox_inches="tight")
