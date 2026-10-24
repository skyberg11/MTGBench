"""The two Wordle figures: selected RU configurations and all EN/RU models."""

import re
from collections import defaultdict

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from ..load_results import read_jsonl

# Separate palettes match the main-text and appendix figures, respectively.
SELECTED = (
    ("deepseek-v4-pro", "reasoning", "DeepSeek V4 Pro\n(Reason)", "#0a77b3"),
    ("deepseek-v4-pro", "answer_only", "DeepSeek V4 Pro (AO)", "#0a77b3"),
    ("gpt-5.4", "reasoning", "GPT 5.4 (Reason)", "#0aa179"),
    ("gpt-5.4", "answer_only", "GPT 5.4 (AO)", "#0aa179"),
    ("gpt-5.4-mini", "reasoning", "GPT 5.4 Mini (Reason)", "#e6a20a"),
    ("gpt-5.4-mini", "answer_only", "GPT 5.4 Mini (AO)", "#e6a20a"),
    (
        "gemini-3.1-pro-preview",
        "reasoning",
        "Gemini 3.1 Pro Preview\n(Reason)",
        "#51b3e2",
    ),
    (
        "qwen3-235b-a22b-thinking-2507",
        "reasoning",
        "Qwen3 235B A22B\nThinking 2507 (Reason)",
        "#efe349",
    ),
    ("qwen3.5-35b-a3b", "reasoning", "Qwen3.5 35B A3B\n(Reason)", "#d6650a"),
    ("qwen3.5-35b-a3b", "answer_only", "Qwen3.5 35B A3B (AO)", "#d6650a"),
)
MODELS = (
    ("deepseek-v3.1-terminus", "DeepSeek V3.1 Term.", "#9c4a00", "o"),
    ("deepseek-v4-flash", "DeepSeek V4 Flash", "#e66101", "D"),
    ("deepseek-v4-pro", "DeepSeek V4 Pro", "#fdb863", "P"),
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview", "#a50f15", "s"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite", "#fb9a99", "^"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Prev.", "#ef3b2c", "v"),
    ("gpt-4.1", "GPT 4.1", "#006d2c", "X"),
    ("gpt-5.4", "GPT 5.4", "#31a354", "h"),
    ("gpt-5.4-mini", "GPT 5.4 Mini", "#a1d99b", "<"),
    ("gpt-5.4-nano", "GPT 5.4 Nano", "#74c476", ">"),
    ("gpt-oss-120b", "GPT OSS 120B", "#238b45", "*"),
    ("qwen3-235b-a22b-instruct-2507", "Qwen3 235B Inst.", "#08519c", "1"),
    ("qwen3-235b-a22b-thinking-2507", "Qwen3 235B Think.", "#2171b5", "2"),
    ("qwen3-30b-a3b-instruct-2507", "Qwen3 30B Inst.", "#4292c6", "3"),
    ("qwen3-30b-a3b-thinking-2507", "Qwen3 30B Think.", "#6baed6", "4"),
    ("qwen3.5-35b-a3b", "Qwen3.5 35B", "#9ecae1", "d"),
    ("human", "Human", "#8064a2", "o"),
)
LINESTYLES = {"answer_only": "-", "cot": "--", "reasoning": "-."}
ANSWER = re.compile(r"(?:Answer|Ответ)\s*:\s*([a-zа-яё]+)", re.IGNORECASE)


def wordle_curve(episode):
    """Best positional match so far, including guesses rejected by the dictionary."""
    best, curve = 0, []
    target = episode["target"].lower().replace("ё", "е")
    for turn in episode["dialogue"]:
        action = turn.get("parsed_action", "")
        matches = ANSWER.findall(action)
        bare = re.fullmatch(r"(?:[a-z]+|[а-яё]+)", action.strip(), re.IGNORECASE)
        guess = (
            (matches[0] if matches else bare.group() if bare else "")
            .lower()
            .replace("ё", "е")
        )
        # The published diagnostic also compares short/long guesses by position.
        best = max(best, sum(a == b for a, b in zip(guess, target)))
        curve.append(best)
    return np.asarray((curve + [best] * 20)[:20], dtype=float)


def diagnostic_score(episode, baselines):
    """Wordle figure normalization; the summary table uses score_episode instead."""
    if not episode["won"]:
        return 0.0
    key = (episode["language"], episode["target"].lower().replace("ё", "е"))
    baseline = baselines[key]
    if not 0 <= baseline < 20:
        raise ValueError(f"Invalid Wordle diagnostic baseline: {key}: {baseline}")
    return float(np.clip(1 - (episode["turns"] - baseline) / (20 - baseline), 0, 1))


def mean_ci(values):
    """Normal 95% interval used in the Wordle figure (unclipped)."""
    values = np.asarray(values, dtype=float)
    if not len(values):
        raise ValueError("Cannot plot an empty Wordle group")
    mean = values.mean(axis=0)
    error = (
        1.96 * values.std(axis=0, ddof=1) / np.sqrt(len(values))
        if len(values) > 1
        else np.zeros_like(mean)
    )
    return mean, error


def collect_series(episodes, root, baselines):
    buckets = {
        (language, row["word"]): int(row["bucket"])
        for language in ("en", "ru")
        for row in read_jsonl(root / f"multiturn_games_benchmark/datasets/wordle/wordle_{language}.jsonl")
    }
    grouped = defaultdict(list)
    for episode in episodes:
        if episode["game"] == "wordle":
            key = (episode["model"], episode["mode"], episode["language"])
            if "wordle_sessions" in episode:
                for session in episode["wordle_sessions"]:
                    grouped[key].append(
                        {
                            "target": episode["target"],
                            "language": episode["language"],
                            "won": session["won"],
                            "turns": session["total_moves"],
                            "dialogue": [
                                {"parsed_action": move["player_answer"]}
                                for move in session["moves"]
                            ],
                        }
                    )
            else:
                grouped[key].append(episode)
    series = {}
    for key, items in grouped.items():
        curves = [wordle_curve(episode) for episode in items]
        progress, progress_error = mean_ci(curves)
        scores, errors = [], []
        for bucket in (1, 2, 3):
            mean, error = mean_ci(
                [
                    diagnostic_score(e, baselines)
                    for e in items
                    if buckets[(e["language"], e["target"])] == bucket
                ]
            )
            scores.append(mean)
            errors.append(error)
        series[key] = (progress, progress_error, np.asarray(scores), np.asarray(errors))
    return series


def save(fig, output, name, **kwargs):
    directory = output / "figures"
    directory.mkdir(parents=True, exist_ok=True)
    # Fixed canvas sizes preserve the paper's panel and legend placement.
    fig.savefig(directory / f"{name}.pdf", **kwargs)
    fig.savefig(directory / f"{name}.png", dpi=300, **kwargs)
    plt.close(fig)


def label_axes(axes, *, selected):
    for row, ax in enumerate(axes):
        ax.set_axisbelow(True)
        ax.grid(
            True,
            alpha=0.25 if selected else 0.6,
            color="#b0b0b0" if selected else "#d0d0d0",
            linewidth=0.8 if selected else 0.6,
        )
        if row == 0:
            ax.set(
                xlim=(1, 20),
                ylim=(0, 5.05 if selected else 5.08),
                xlabel="Move number",
                ylabel="Best revealed positions",
            )
            ax.set_xticks([1, 5, 10, 15, 20])
            ax.set_yticks(range(6))
        else:
            ax.set(
                xlim=(0.9, 3.1),
                ylim=(0, 1.01),
                xlabel="Word difficulty",
                ylabel="Wordle score",
            )
            ax.set_xticks([1, 2, 3], ["Easy", "Medium", "Hard"])
            ax.set_yticks(np.linspace(0, 1, 6))
        if not selected:
            ax.spines[["top", "right"]].set_visible(False)
            ax.spines[["bottom", "left"]].set_color("#333333")
            ax.spines[["bottom", "left"]].set_linewidth(0.6)
            ax.tick_params(width=0.6, length=2.5)


def selected_plot(series, output):
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 17,
            "axes.labelsize": 20,
            "axes.labelweight": "bold",
            "legend.fontsize": 14.5,
        }
    ):
        fig, axes = plt.subplots(2, 1, figsize=(9.6, 8.4))
        fig.subplots_adjust(left=0.105, right=0.62, bottom=0.105, top=0.95, hspace=0.34)
        label_axes(axes, selected=True)
        for model, mode, label, color in SELECTED:
            progress, progress_error, scores, errors = series[(model, mode, "ru")]
            style = {
                "color": color,
                "linestyle": LINESTYLES[mode],
                "marker": "o",
                "linewidth": 2.8,
                "markersize": 5.5,
                "label": label,
            }
            axes[0].plot(range(1, 21), progress, markevery=2, **style)
            axes[0].fill_between(
                range(1, 21),
                progress - progress_error,
                progress + progress_error,
                color=color,
                alpha=0.12,
                linewidth=0,
            )
            axes[1].errorbar(
                [1, 2, 3], scores, yerr=errors, capsize=4, elinewidth=1.2, **style
            )
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            loc="center left",
            bbox_to_anchor=(0.65, 0.5),
            frameon=False,
            handlelength=2.6,
            labelspacing=0.55,
        )
        save(fig, output, "combined_selected_ci")


def all_models_plot(series, output):
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.labelsize": 9,
            "axes.labelweight": "bold",
            "axes.titlesize": 9,
            "axes.titleweight": "bold",
            "legend.fontsize": 7,
        }
    ):
        fig, axes = plt.subplots(2, 2, figsize=(7.15, 6.9))
        fig.subplots_adjust(
            left=0.075, right=0.995, bottom=0.2, top=0.97, wspace=0.26, hspace=0.26
        )
        for column, language in enumerate(("en", "ru")):
            label_axes(axes[:, column], selected=False)
            axes[0, column].set_title(language.upper(), pad=3)
            for model, _, color, marker in MODELS:
                for mode, linestyle in LINESTYLES.items():
                    key = (model, mode, language)
                    if key not in series:
                        continue
                    progress, _, scores, _ = series[key]
                    style = {
                        "color": color,
                        "marker": marker,
                        "linestyle": linestyle,
                        "linewidth": 1.35,
                        "markersize": 2.4 if model == "human" else 2.8,
                    }
                    axes[0, column].plot(range(1, 21), progress, markevery=2, **style)
                    axes[1, column].plot([1, 2, 3], scores, **style)
        handles = [
            Line2D(
                [],
                [],
                color=color,
                marker=marker,
                label=label,
                linewidth=1.4,
                markersize=3,
            )
            for _, label, color, marker in MODELS
        ]
        handles += [
            Line2D(
                [],
                [],
                color="#333333",
                linestyle=LINESTYLES[mode],
                label=label,
                linewidth=1.4,
            )
            for mode, label in (
                ("answer_only", "AO"),
                ("cot", "CoT"),
                ("reasoning", "R"),
            )
        ]
        fig.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.01),
            ncol=5,
            frameon=False,
            handlelength=2.4,
            columnspacing=1.2,
            labelspacing=0.5,
        )
        save(fig, output, "combined_all_no_ci")


def plot_wordle(episodes, root, output, baselines):
    series = collect_series(episodes, root, baselines)
    selected_plot(series, output)
    all_models_plot(series, output)
