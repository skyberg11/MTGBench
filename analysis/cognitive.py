"""Cognitive benchmark scores and their Kendall correlation with game scores."""

import csv
import json
from collections import defaultdict

from scipy.stats import kendalltau

from .scoring import GAMES

# Paper order: executive core, executive higher-order, socio-emotional.
SKILLS = (
    ("working_memory", "Working Mem.", "WM"),
    ("cognitive_flexibility", "Cog. Flex.", "CogFlex"),
    ("causal_reasoning", "Causal R.", "Causal"),
    ("logical_reasoning", "Logical R.", "Logical"),
    ("commonsense_reasoning", "Commonsense R.", "Common."),
    ("planning", "Planning", "Plan"),
    ("emotional_intelligence", "Emo. Int.", "EQ"),
    ("pragmatics", "Pragmatics", "Pragm."),
    ("social_commonsense", "Social Common-sense", "SocCom."),
    ("theory_of_mind", "Theory of Mind", "ToM"),
    ("attribution_judgment", "Attrib. & Judgm.", "Attrib."),
)
GENERAL_SKILLS = {key for key, *_ in SKILLS[:6]}
# Multi-turn benchmarks kept no transcripts, only these session-level scores.
MULTITURN_SKILLS = ("working_memory", "cognitive_flexibility")
# Cognitive runs used a different identifier for this model than the game runs.
ALIASES = {"gemini-3-flash": "gemini-3-flash-preview"}
# Appendix table rows (answer-only models).
TABLE_MODELS = (
    ("qwen3-30b-a3b-instruct-2507", "Qwen3 30B A3B Instruct 2507"),
    ("qwen3-235b-a22b-instruct-2507", "Qwen3 235B A22B Instruct 2507"),
    ("qwen3.5-35b-a3b", "Qwen3.5 35B A3B"),
    ("deepseek-v3.1-terminus", "DeepSeek V3.1 Terminus"),
    ("deepseek-v4-flash", "DeepSeek 4 Flash"),
    ("deepseek-v4-pro", "DeepSeek 4 Pro"),
    ("gpt-4.1", "GPT 4.1"),
    ("gpt-5.4-nano", "GPT 5.4 nano"),
    ("gpt-5.4-mini", "GPT 5.4 mini"),
    ("gpt-5.4", "GPT 5.4"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite Preview"),
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview"),
)
MIN_PAIRS = 5


def load_cognitive_scores(root):
    """Per-model scores: accuracy, or mean EQ score / 100 for emotional intelligence."""
    base = root / "results/cognitive"
    scores = {}
    for path in sorted((base / "trajectories/single_turn").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        totals = defaultdict(lambda: [0, 0.0])
        for item in data["items"]:
            cell = totals[item["benchmark"]]
            cell[0] += 1
            if item["benchmark"] == "emotional_intelligence":
                cell[1] += (
                    float(item["score"]) if item.get("score") is not None else 0.0
                )
            elif item.get("correct"):
                cell[1] += 1
        scores[ALIASES.get(data["model"], data["model"])] = {
            bench: total / n / 100.0 if bench == "emotional_intelligence" else total / n
            for bench, (n, total) in totals.items()
        }
    with (base / "multiturn_scores.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            model = ALIASES.get(row["model"], row["model"])
            scores[model] |= {
                k: float(row[k]) for k in MULTITURN_SKILLS if row[k].strip()
            }
    return scores


def game_scores(rows):
    """Answer-only English game means from the summary-table rows."""
    return {
        (row["model"], row["game"]): row["score"]
        for row in rows
        if row["mode"] == "answer_only"
        and row["language"] == "en"
        and row["game"] in GAMES
    }


def kendall_matrix(cognitive, rows):
    games = game_scores(rows)
    cells = []
    for skill, *_ in SKILLS:
        for game in GAMES:
            pairs = [
                (scores[skill], games[(model, game)])
                for model, scores in sorted(cognitive.items())
                if skill in scores and (model, game) in games
            ]
            if len(pairs) < MIN_PAIRS:
                continue
            result = kendalltau(*zip(*pairs), variant="b")
            cells.append(
                {
                    "skill": skill,
                    "game": game,
                    "n": len(pairs),
                    "tau_b": float(result.correlation),
                    "p_value": float(result.pvalue),
                    "significant": bool(result.pvalue < 0.05),
                }
            )
    return cells


def write_cognitive_tables(cognitive, matrix, output):
    directory = output / "tables"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "cognitive_correlation_kendall.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(matrix[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(matrix)
    keys = [key for key, *_ in SKILLS]
    with (directory / "cognitive_scores.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["model", *keys])
        for model, scores in sorted(cognitive.items()):
            writer.writerow([model, *(scores.get(k, "") for k in keys)])
    groups = (
        ("Executive (Core)", 2),
        ("Executive (Higher-order)", 4),
        ("Socio-emotional", 5),
    )
    tex = "\\begin{tabular}{l" + " r" * len(SKILLS) + "}\n\\toprule\n"
    tex += (
        "\\multirow{2}{*}{Model} & "
        + " & ".join(f"\\multicolumn{{{n}}}{{c}}{{{name}}}" for name, n in groups)
        + " \\\\\n\\cmidrule(lr){2-3}\\cmidrule(lr){4-7}\\cmidrule(l){8-12}\n"
    )
    tex += " & " + " & ".join(short for *_, short in SKILLS) + " \\\\\n\\midrule\n"
    for model, name in TABLE_MODELS:
        scores = cognitive.get(model, {})
        tex += (
            " & ".join(
                [name] + [f"{scores[k]:.2f}" if k in scores else "--" for k in keys]
            )
            + " \\\\\n"
        )
    (directory / "cognitive_scores.tex").write_text(
        tex + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8"
    )
