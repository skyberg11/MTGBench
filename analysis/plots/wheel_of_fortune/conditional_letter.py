"""Wheel of Fortune letter choices: conditional versus marginal corpus ranks.

For each new letter guess, rank the chosen letter class under two corpus
distributions: P_cond over nouns of the target's length that match the
revealed pattern, and P_marg over all nouns of that length. Lines show the mean
of rank_cond - rank_marg by reveal stage; negative values indicate guesses
that use the revealed information.
"""

import csv
from collections import defaultdict
from functools import cache

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from dataset_generation.wheel_of_fortune.freq_dict import freq_dict_path

from ...aggregate import bca_mean_ci
from ...scoring import letter_classes
from ..wordle import save

EN_CORPUS = "multiturn_games_benchmark/datasets/wheel_of_fortune/en_wordnet_nouns.csv"
ALPHABETS = {
    "ru": "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
    "en": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
}
# Main-text configurations; each model keeps one colour and marker.
SELECTED = (
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview", "#0072B2", "o"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview", "#009E73", "s"),
    ("qwen3.5-35b-a3b", "Qwen3.5 35B A3B", "#E69F00", "^"),
    ("human", "Human", "#CC79A7", "D"),
)
MODES = {"answer_only": "AO", "cot": "CoT", "reasoning": "Reason"}
BINS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))
MIN_N = 10


@cache
def extract_guess(language):
    """The environment's own parser, so replays see the guesses the game saw."""
    from multiturn_games_benchmark.games.field_of_miracles_game import (
        FieldOfMiraclesGame,
    )

    return FieldOfMiraclesGame(
        game_id="replay", word="_", language=language
    )._extract_guess


def load_corpus(root, language):
    """Distinct noun lemmas within the game alphabet, grouped by length."""
    alphabet = set(ALPHABETS[language])
    words = {}
    path = freq_dict_path() if language == "ru" else root / EN_CORPUS
    with path.open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            lemma = (row.get("lemma") or "").strip().upper()
            if row.get("pos") == "s" and lemma and set(lemma) <= alphabet:
                words.setdefault(lemma)
    by_length = defaultdict(list)
    for word in words:
        classes = letter_classes(word, language)
        by_length[len(word)].append((word, classes, set(classes)))
    return by_length


def guesses(episode):
    """(guess, is_word_guess) for each valid move."""
    if "moves" in episode:  # human session
        for move in episode["moves"]:
            if move.get("is_valid", True):
                meta = move.get("metadata") or {}
                yield (meta.get("guess") or "").upper(), bool(meta.get("is_word_guess"))
        return
    parse = extract_guess(episode["language"])
    for turn in episode["dialogue"]:
        if turn.get("is_valid", True):
            guess, is_word = parse(turn.get("parsed_action") or "")
            yield guess.upper(), is_word


def replay(episode, language, corpus, tie_order):
    """Yield (reveal fraction, rank_cond - rank_marg, oracle delta) per new letter."""
    target = episode["target"].upper()
    if not target or not set(target) <= set(ALPHABETS[language]):
        return
    candidates = corpus.get(len(target), [])
    if not candidates:
        return
    target_classes = letter_classes(target, language)
    target_set = set(target_classes)
    presence = defaultdict(int)
    for _, _, present in candidates:
        for c in present:
            presence[c] += 1
    revealed = [False] * len(target)
    guessed = set()
    for guess, is_word in guesses(episode):
        if not guess:
            continue
        if is_word:
            if guess == target:
                return
            continue
        cls = letter_classes(guess, language)
        if cls not in tie_order or cls in guessed:
            continue
        reveal = len({c for c, r in zip(target_classes, revealed) if r}) / len(
            target_set
        )
        remaining = [c for c in tie_order if c not in guessed]
        hidden = [i for i, r in enumerate(revealed) if not r]
        matching = [
            classes
            for word, classes, _ in candidates
            if all(
                word[i] == target[i] if revealed[i] else classes[i] not in guessed
                for i in range(len(target))
            )
        ]
        p_cond = {
            c: (
                sum(any(classes[i] == c for i in hidden) for classes in matching)
                / len(matching)
                if matching and hidden
                else 0.0
            )
            for c in remaining
        }
        p_marg = {c: presence[c] / len(candidates) for c in remaining}
        # Ties break by the class's lowest code point, as in the paper.
        by_cond = sorted(remaining, key=lambda c: (-p_cond[c], tie_order[c]))
        by_marg = sorted(remaining, key=lambda c: (-p_marg[c], tie_order[c]))
        rank_cond, rank_marg = by_cond.index(cls) + 1, by_marg.index(cls) + 1
        yield reveal, rank_cond - rank_marg, 1 - (by_marg.index(by_cond[0]) + 1)
        guessed.add(cls)
        revealed = [r or c == cls for c, r in zip(target_classes, revealed)]


def bin_of(reveal):
    for low, high in BINS:
        if low <= reveal < high or reveal == high == 1.0:
            return low, high


def collect_cells(episodes, root, resamples, seed):
    rows = []
    for language in ("ru", "en"):
        corpus = load_corpus(root, language)
        tie_order = {}
        for letter in sorted(ALPHABETS[language]):  # code-point order
            tie_order.setdefault(letter_classes(letter, language), letter)
        series = defaultdict(list)
        for e in episodes:
            if e["game"] == "wheel_of_fortune" and e["language"] == language:
                if e["model"] == "human":
                    series[(e["model"], e["mode"])].extend(
                        {**session, "language": language}
                        for session in e["wheel_of_fortune_sessions"]
                    )
                else:
                    series[(e["model"], e["mode"])].append(e)
        for model, *_ in SELECTED:
            for mode in MODES:
                records = defaultdict(list)
                for episode in series.get((model, mode), []):
                    for reveal, delta, oracle in replay(
                        episode, language, corpus, tie_order
                    ):
                        records[bin_of(reveal)].append((delta, oracle))
                for low, high in BINS:
                    values = records[(low, high)]
                    if not values:
                        continue
                    mean, ci_low, ci_high = bca_mean_ci(
                        [d for d, _ in values], resamples=resamples, seed=seed
                    )
                    rows.append(
                        {
                            "language": language,
                            "model": model,
                            "mode": mode,
                            "reveal_bin": f"{int(100 * low)}-{int(100 * high)}%",
                            "n": len(values),
                            "delta_rank": mean,
                            "delta_rank_ci_low": ci_low,
                            "delta_rank_ci_high": ci_high,
                            "oracle_delta_rank": float(np.mean([o for _, o in values])),
                        }
                    )
    return rows


def plot_language(rows, language, output):
    labels = [f"{int(100 * low)}-{int(100 * high)}%" for low, high in BINS]
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    for model, label, color, marker in SELECTED:
        human = model == "human"
        for mode, mode_label in MODES.items():
            cells = [
                r
                for r in rows
                if (r["language"], r["model"], r["mode"]) == (language, model, mode)
                and r["n"] >= MIN_N
            ]
            if not cells:
                continue
            xs = [labels.index(r["reveal_bin"]) for r in cells]
            ys = [r["delta_rank"] for r in cells]
            line, _, _ = ax.errorbar(
                xs,
                ys,
                yerr=[
                    [max(0.0, r["delta_rank"] - r["delta_rank_ci_low"]) for r in cells],
                    [
                        max(0.0, r["delta_rank_ci_high"] - r["delta_rank"])
                        for r in cells
                    ],
                ],
                color=color,
                marker=marker,
                markersize=9 if human else 7,
                linewidth=2.2 if human else 1.6,
                linestyle="-" if mode == "answer_only" else "-.",
                capsize=4 if human else 3,
                capthick=1.2 if human else 0.9,
                label=label if human else f"{label} ({mode_label})",
                alpha=1.0 if human else 0.95,
                zorder=5 if human else 2,
            )
            # Styled after the call: errorbar's markeredgewidth would also thin the caps.
            line.set_markeredgecolor("white" if human else "none")
            line.set_markeredgewidth(1.0 if human else 0)
            ax.plot(
                xs,
                [r["oracle_delta_rank"] for r in cells],
                color=color,
                linestyle=":",
                linewidth=1.9,
                alpha=0.7,
            )
    ax.set_xticks(range(len(labels)), labels, fontsize=13)
    ax.tick_params(axis="y", labelsize=13)
    ax.set_xlabel("Reveal % at turn (binned)", fontsize=15, fontweight="bold")
    ax.set_ylabel(
        "Mean rank_cond − rank_marg\n(negative ⇒ aligns with conditional)",
        fontsize=15,
        fontweight="bold",
    )
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    ax.axhline(y=0, color="grey", linestyle="--", linewidth=1.2, alpha=0.8)
    styles = ax.legend(
        handles=[
            Line2D([0], [0], color="black", linestyle="-", linewidth=1.6, label="AO"),
            Line2D(
                [0],
                [0],
                color="black",
                linestyle="-.",
                linewidth=1.6,
                label="CoT/Reason",
            ),
            Line2D(
                [0],
                [0],
                color="black",
                linestyle=":",
                linewidth=1.9,
                label="Δ_oracle ceiling",
            ),
        ],
        loc="lower left",
        fontsize=12,
        framealpha=0.5,
        title="Line style",
        title_fontsize=12,
    )
    ax.add_artist(styles)
    handles, names = ax.get_legend_handles_labels()
    ncol = min(2, len(names))
    rows_needed = (len(names) + ncol - 1) // ncol
    fig.subplots_adjust(
        left=0.14, right=0.97, top=0.82, bottom=max(0.18, 0.10 + 0.04 * rows_needed)
    )
    fig.legend(
        handles,
        names,
        loc="lower center",
        ncol=ncol,
        frameon=False,
        fontsize=13,
        bbox_to_anchor=(0.5, 0.0),
    )
    # Cropped like the paper's figure, so it scales to the column the same way.
    # TrueType fonts, as in the paper: ACL's checker rejects the default Type 3.
    with matplotlib.rc_context({"pdf.fonttype": 42}):
        save(
            fig,
            output,
            f"wheel_of_fortune_conditional_letter_alignment_delta_only_{language}",
            bbox_inches="tight",
        )


def plot_conditional_letter(episodes, root, output, resamples=10000, seed=42):
    rows = collect_cells(episodes, root, resamples, seed)
    directory = output / "tables"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "wheel_of_fortune_conditional_letter_alignment.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for language in ("ru", "en"):
        plot_language(rows, language, output)
