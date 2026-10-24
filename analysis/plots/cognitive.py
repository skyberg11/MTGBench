"""Cognitive skills against game scores: Kendall matrix and paired radar charts."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import Patch

from ..cognitive import GENERAL_SKILLS, SKILLS, game_scores
from ..scoring import GAMES
from .wordle import save

GAME_LABELS = {
    "wordle": "Wordle",
    "word_chain": "Word Chain",
    "situation_puzzles": "Situation Puzzles",
    "twenty_questions": "20 Questions",
    "wheel_of_fortune": "Wheel of Fortune",
    "twenty_features": "20 Features",
    "alias": "Alias",
}
GROUP_COLORS = {"general": "#7B68EE", "social": "#2E8B57"}


def plot_matrix(matrix, output):
    skills = [s for s in SKILLS if any(c["skill"] == s[0] for c in matrix)]
    games = [g for g in GAMES if any(c["game"] == g for c in matrix)]
    cells = {(c["skill"], c["game"]): c for c in matrix}
    values = np.array(
        [
            [cells[(s, g)]["tau_b"] if (s, g) in cells else np.nan for g in games]
            for s, *_ in skills
        ]
    )
    cmap = sns.color_palette("mako_r", as_cmap=True)
    norm = plt.Normalize(vmin=0, vmax=1)
    fig, ax = plt.subplots(
        figsize=(max(6, len(games) * 1.7 + 2.7), max(5, len(skills) * 0.62 + 2.1))
    )
    image = ax.imshow(values, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(
        range(len(games)),
        [GAME_LABELS[g] for g in games],
        rotation=45,
        ha="right",
        fontsize=18,
    )
    ax.set_yticks(range(len(skills)), [label for _, label, _ in skills], fontsize=18)
    for tick, (skill, *_) in zip(ax.get_yticklabels(), skills):
        tick.set_color(GROUP_COLORS["general" if skill in GENERAL_SKILLS else "social"])
    for i, (skill, *_) in enumerate(skills):
        for j, game in enumerate(games):
            cell = cells.get((skill, game))
            if cell is None:
                ax.text(
                    j,
                    i,
                    "N/A",
                    ha="center",
                    va="center",
                    fontsize=19,
                    color="gray",
                    fontweight="bold",
                )
                continue
            r, g, b, _ = cmap(norm(cell["tau_b"]))
            ax.text(
                j,
                i,
                f"{cell['tau_b']:.2f}" + ("*" if cell["significant"] else ""),
                ha="center",
                va="center",
                fontsize=19,
                fontweight="bold",
                color="white" if 0.299 * r + 0.587 * g + 0.114 * b < 0.5 else "black",
            )
            if cell["significant"]:
                ax.add_patch(
                    plt.Rectangle(
                        (j - 0.5, i - 0.5),
                        1,
                        1,
                        fill=False,
                        edgecolor="black",
                        linewidth=2.5,
                    )
                )
    for group, members in (
        ("general", [i for i, (s, *_) in enumerate(skills) if s in GENERAL_SKILLS]),
        ("social", [i for i, (s, *_) in enumerate(skills) if s not in GENERAL_SKILLS]),
    ):
        if len(members) >= 2:
            ax.add_patch(
                plt.Rectangle(
                    (-0.5, min(members) - 0.5),
                    len(games),
                    max(members) - min(members) + 1,
                    fill=False,
                    edgecolor=GROUP_COLORS[group],
                    linewidth=2.5,
                    clip_on=False,
                )
            )
    colorbar = fig.colorbar(image, ax=ax, shrink=0.8, pad=0.02)
    colorbar.set_label("Kendall τ-b", fontsize=18)
    colorbar.ax.tick_params(labelsize=15)
    ax.legend(
        handles=[
            Patch(
                facecolor="none",
                edgecolor=GROUP_COLORS["general"],
                linewidth=2,
                label="General Cognitive",
            ),
            Patch(
                facecolor="none",
                edgecolor=GROUP_COLORS["social"],
                linewidth=2,
                label="Social / Emotional",
            ),
            Patch(facecolor="none", edgecolor="black", linewidth=2.5, label="p < 0.05"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.44),
        ncol=3,
        fontsize=17,
        frameon=False,
    )
    # The paper's layout reserved a title that its PDF then left blank; reserving
    # it here too and cropping reproduces the figure's size and aspect.
    ax.set_title(
        "Cognitive Skills vs Game Performance (Kendall τ-b)",
        fontsize=24,
        fontweight="bold",
        pad=14,
    )
    fig.tight_layout()
    ax.set_title("")
    # TrueType fonts, as in the paper: ACL's checker rejects the default Type 3.
    with matplotlib.rc_context({"pdf.fonttype": 42}):
        save(fig, output, "cognitive_correlation_matrix_kendall", bbox_inches="tight")


def plot_radar(data, dims, labels, title, output, name):
    """One closed polygon per model on a fixed 0-1 scale (missing values plot as 0)."""
    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    for i, (model, scores) in enumerate(data.items()):
        values = [scores.get(d, 0.0) for d in dims]
        color = plt.cm.tab10(i % 10)
        ax.plot(
            angles + angles[:1],
            values + values[:1],
            "o-",
            linewidth=1.8,
            label=model,
            color=color,
            markersize=4,
        )
        ax.fill(angles + angles[:1], values + values[:1], alpha=0.10, color=color)
    ax.set_thetagrids(
        np.degrees(angles), labels, fontsize=9, color="#333333", fontweight="bold"
    )
    ax.set_ylim(0, 1)
    ax.set_yticks(
        [0.2, 0.4, 0.6, 0.8, 1.0],
        ["0.2", "0.4", "0.6", "0.8", "1.0"],
        fontsize=7,
        color="#666666",
    )
    ax.set_rlabel_position(90)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=22)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=2,
        fontsize=8,
        frameon=False,
    )
    fig.tight_layout()
    # TrueType fonts, as in the paper: ACL's checker rejects the default Type 3.
    with matplotlib.rc_context({"pdf.fonttype": 42}):
        save(fig, output, name, bbox_inches="tight")


def plot_cognitive(matrix, cognitive, rows, output):
    plot_matrix(matrix, output)
    # Trajectory-file order (gpt-5.4-mini before gpt-5.4) keeps the paper's colours.
    models = sorted(cognitive, key=lambda m: f"{m}.json")
    plot_radar(
        {m: cognitive[m] for m in models},
        [key for key, *_ in SKILLS],
        [label for _, label, _ in SKILLS],
        "Cognitive Benchmark Scores",
        output,
        "cognitive_radar_skills",
    )
    games = game_scores(rows)
    plot_radar(
        {m: {g: games[(m, g)] for g in GAMES if (m, g) in games} for m in models},
        list(GAMES),
        [f"{GAME_LABELS[g]} (EN, AO)" for g in GAMES],
        "Game Performance",
        output,
        "cognitive_radar_games",
    )
