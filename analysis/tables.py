"""One summary table containing scores, win rates and their 95% intervals."""

import csv

from .scoring import GAMES


def write_tables(rows, output):
    directory = output / "tables"
    directory.mkdir(parents=True, exist_ok=True)
    order = {game: i for i, game in enumerate((*GAMES, "Total"))}
    rows = sorted(
        rows, key=lambda r: (r["model"], r["mode"], r["language"], order[r["game"]])
    )
    columns = [
        "model",
        "mode",
        "language",
        "game",
        "n",
        "score",
        "score_ci_low",
        "score_ci_high",
        "win_rate",
        "win_rate_ci_low",
        "win_rate_ci_high",
    ]
    with (directory / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    headers = [
        "Model",
        "Mode",
        "Language",
        "Game",
        "N",
        "Score [95% CI]",
        "Win rate [95% CI]",
    ]
    rendered = [
        [str(row[c]) for c in columns[:5]]
        + [
            f"{row[m]:.3f} [{row[m + '_ci_low']:.3f}, {row[m + '_ci_high']:.3f}]"
            for m in ("score", "win_rate")
        ]
        for row in rows
    ]
    md = (
        "| "
        + " | ".join(headers)
        + " |\n| "
        + " | ".join(["---"] * len(headers))
        + " |\n"
    )
    md += "".join("| " + " | ".join(values) + " |\n" for values in rendered)
    (directory / "summary.md").write_text(md, encoding="utf-8")
    tex = "\\begin{longtable}{llllrrr}\n"
    tex += " & ".join(headers).replace("%", r"\%") + r" \\" + "\n"
    tex += "".join(
        " & ".join(values).replace("_", r"\_") + r" \\" + "\n" for values in rendered
    )
    (directory / "summary.tex").write_text(tex + "\\end{longtable}\n", encoding="utf-8")
