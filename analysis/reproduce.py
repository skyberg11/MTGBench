"""Compute the summary and cognitive tables and the paper's figures locally."""

import argparse
import json
from pathlib import Path

from .aggregate import aggregate
from .cognitive import kendall_matrix, load_cognitive_scores, write_cognitive_tables
from .human import load_human_results
from .load_results import load_baselines, load_llm_results
from .scoring import score_episode
from .tables import write_tables


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output-dir", type=Path, default=Path("analysis/outputs"))
    parser.add_argument(
        "--resamples",
        type=int,
        default=10000,
        help="Bootstrap replicates for the summary table and figure intervals",
    )
    parser.add_argument("--seed", type=int, default=42, help="Bootstrap seed")
    parser.add_argument("--no-plots", action="store_true", help="Write only the tables")
    args = parser.parse_args()
    if args.resamples < 1:
        parser.error("--resamples must be positive")
    root, output = args.repo_root.resolve(), args.output_dir.resolve()
    episodes, excluded, _ = load_llm_results(root)
    humans, human_sessions = load_human_results(root)
    baselines = load_baselines(root)
    episodes.extend(humans)
    for episode in episodes:
        episode["score"] = score_episode(episode, baselines)
    rows = aggregate(episodes, resamples=args.resamples, seed=args.seed)
    write_tables(rows, output)
    cognitive = load_cognitive_scores(root)
    matrix = kendall_matrix(cognitive, rows)
    write_cognitive_tables(cognitive, matrix, output)
    if not args.no_plots:
        from .plots import (
            plot_cognitive,
            plot_wheel_of_fortune,
            plot_wordle,
        )

        plot_wordle(episodes, root, output, baselines)
        plot_wheel_of_fortune(episodes, root, output, args.resamples, args.seed)
        plot_cognitive(matrix, cognitive, rows, output)
    print(
        json.dumps(
            {
                "llm_episodes": len(episodes) - len(humans),
                "excluded_episodes": len(excluded),
                "human_sessions": human_sessions,
                "human_targets": len(humans),
                "summary_rows": len(rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
