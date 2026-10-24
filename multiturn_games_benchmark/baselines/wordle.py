"""
Algorithmic Wordle solver using entropy-maximizing heuristic.

Loads the word list from multiturn_games_benchmark/datasets/wordle/wordle_en.jsonl and plays
Wordle using a greedy heuristic that chooses guesses that maximize expected information gain
(Shannon entropy over the distribution of feedback patterns).

Usage:
    # Generate a single trajectory
    python -m multiturn_games_benchmark.baselines.wordle --target story

    # Generate trajectories for all words and save results
    python -m multiturn_games_benchmark.baselines.wordle --all --max-attempts 6 --output results/heuristic_wordle.json

    # Generate trajectories for first N words
    python -m multiturn_games_benchmark.baselines.wordle --num-games 50 --max-attempts 6 --seed 42
"""

import csv
import json
import math
import os
import time
import argparse
import random
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAY = 0
YELLOW = 1
GREEN = 2

FEEDBACK_NAMES = {GRAY: "Серый", YELLOW: "Желтый", GREEN: "Зеленый"}

DEFAULT_DATASET = str(Path(__file__).resolve().parents[1] / "datasets/wordle/wordle_en.jsonl")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_words(dataset_path: str = DEFAULT_DATASET) -> List[str]:
    """Load published JSONL words, or a legacy CSV with a Слово column."""
    with open(dataset_path, encoding="utf-8") as stream:
        rows = (json.loads(line) for line in stream if line.strip()) if str(dataset_path).endswith(".jsonl") else csv.DictReader(stream)
        words = [str(row.get("word", row.get("Слово", ""))).strip().lower().replace("ё", "е") for row in rows]
    words = list(dict.fromkeys(word for word in words if len(word) == 5 and word.isalpha()))
    if not words:
        raise ValueError(f"No five-letter words in {dataset_path}")
    return words


# ---------------------------------------------------------------------------
# Feedback computation
# ---------------------------------------------------------------------------


def compute_feedback(guess: str, target: str) -> Tuple[int, ...]:
    """Return a feedback pattern as a tuple of (GREEN / YELLOW / GRAY).

    The logic **exactly** mirrors ``WordleJudge.evaluate_player_move`` in
    ``multiturn_games_benchmark/games/wordle_game.py``:

    * First pass  – mark exact matches as GREEN.
    * Second pass – if the letter is not GREEN but exists *anywhere* in the
      target, mark it YELLOW; otherwise GRAY.

    Note: the existing judge does **not** decrement letter counts, so a letter
    that appears once in the target can produce multiple YELLOWs.  We replicate
    that behaviour for full compatibility.
    """
    pattern = [GRAY] * 5
    target_set = set(target)

    # First pass: greens
    for i in range(5):
        if guess[i] == target[i]:
            pattern[i] = GREEN

    # Second pass: yellows
    for i in range(5):
        if pattern[i] == GRAY and guess[i] in target_set:
            pattern[i] = YELLOW

    return tuple(pattern)


def feedback_to_text(guess: str, pattern: Tuple[int, ...]) -> str:
    """Format a feedback pattern in the same human-readable style used by
    ``WordleJudge``."""
    green_lines: List[str] = []
    yellow_lines: List[str] = []
    gray_lines: List[str] = []

    for i, code in enumerate(pattern):
        letter = guess[i]
        if code == GREEN:
            green_lines.append(
                f'- Правильно. Буква "{letter}" точно стоит на {i + 1}-м месте.'
            )
        elif code == YELLOW:
            yellow_lines.append(
                f'- Буква "{letter}" не может стоять на {i + 1}-м месте, но есть в слове.'
            )
        else:
            gray_lines.append(f'- Буквы "{letter}" точно нет в слове.')

    green_part = "\n".join(green_lines)
    yellow_part = "\n".join(yellow_lines)
    gray_part = "\n".join(gray_lines)

    return (
        f"1.  ЗЕЛЕНЫЕ БУКВЫ (точное местоположение):\n{green_part}\n\n"
        f"2.  ЖЕЛТЫЕ БУКВЫ (есть в слове, но стоят не на этих местах):\n{yellow_part}\n\n"
        f"3.  СЕРЫЕ БУКВЫ (этих букв точно нет в слове):\n{gray_part}\n"
    )


# ---------------------------------------------------------------------------
# Candidate filtering
# ---------------------------------------------------------------------------


def filter_candidates(
    candidates: List[str], guess: str, pattern: Tuple[int, ...]
) -> List[str]:
    """Keep only candidates that would produce *exactly* ``pattern`` if they
    were the target and ``guess`` was played."""
    return [w for w in candidates if compute_feedback(guess, w) == pattern]


# ---------------------------------------------------------------------------
# Entropy-based scoring
# ---------------------------------------------------------------------------


def score_guess_entropy(guess: str, candidates: List[str]) -> float:
    """Compute the Shannon entropy (in bits) of the feedback-pattern
    distribution that ``guess`` produces over ``candidates``.

    Higher entropy → the guess splits candidates more evenly → more
    information gained on average.
    """
    pattern_counts: Counter = Counter()
    for target in candidates:
        pattern_counts[compute_feedback(guess, target)] += 1

    total = len(candidates)
    entropy = 0.0
    for count in pattern_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


@dataclass
class SolverMove:
    """One move inside a solver trajectory."""
    move_number: int
    guess: str
    feedback_pattern: Tuple[int, ...]
    feedback_text: str
    candidates_before: int
    candidates_after: int


@dataclass
class SolverResult:
    """Full result of solving one word."""
    target: str
    won: bool
    total_moves: int
    moves: List[SolverMove] = field(default_factory=list)
    duration_seconds: float = 0.0


class WordleSolver:
    """Entropy-maximising Wordle solver.

    Parameters
    ----------
    words : list[str]
        The full vocabulary (both for guessing and as initial candidate set).
    max_attempts : int
        Maximum number of guesses allowed (default 6).
    """

    def __init__(self, words: List[str], max_attempts: int = 6):
        self.all_words = list(words)
        self.max_attempts = max_attempts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def solve(self, target: str) -> SolverResult:
        """Play a full game for *target* and return the trajectory."""
        target = target.lower().replace("ё", "е")
        start = time.time()

        candidates = list(self.all_words)
        moves: List[SolverMove] = []

        for attempt in range(1, self.max_attempts + 1):
            guess = self._pick_guess(candidates, attempt)
            pattern = compute_feedback(guess, target)
            fb_text = feedback_to_text(guess, pattern)

            new_candidates = filter_candidates(candidates, guess, pattern)

            moves.append(
                SolverMove(
                    move_number=attempt,
                    guess=guess,
                    feedback_pattern=pattern,
                    feedback_text=fb_text,
                    candidates_before=len(candidates),
                    candidates_after=len(new_candidates),
                )
            )

            # Check win
            if guess == target:
                return SolverResult(
                    target=target,
                    won=True,
                    total_moves=attempt,
                    moves=moves,
                    duration_seconds=time.time() - start,
                )

            candidates = new_candidates

        # Out of attempts
        return SolverResult(
            target=target,
            won=False,
            total_moves=self.max_attempts,
            moves=moves,
            duration_seconds=time.time() - start,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _pick_guess(self, candidates: List[str], attempt: int) -> str:
        """Choose the best guess for the current candidate set."""
        # If only one candidate left, guess it.
        if len(candidates) == 1:
            return candidates[0]

        # If two candidates left, just pick the first one.
        if len(candidates) == 2:
            return candidates[0]

        # First guess is random from the full vocabulary.
        if attempt == 1:
            return random.choice(self.all_words)

        # If candidate set is small, restrict guesses to candidates only
        # (a guess from candidates can also be the answer).
        if len(candidates) <= 20:
            return self._best_by_entropy(candidates, pool=candidates)

        # Otherwise pick from full vocabulary but prefer candidates.
        return self._best_by_entropy(candidates, pool=self.all_words)

    def _best_by_entropy(
        self,
        candidates: List[str],
        pool: Optional[List[str]] = None,
    ) -> str:
        """Return the word from *pool* that maximises entropy over
        *candidates*.  When tied, prefer a word that is itself a candidate."""
        if pool is None:
            pool = candidates

        best_word = pool[0]
        best_entropy = -1.0
        best_is_candidate = False

        candidate_set = set(candidates)

        for word in pool:
            ent = score_guess_entropy(word, candidates)
            is_cand = word in candidate_set

            # Prefer higher entropy; break ties in favour of candidates.
            if (ent > best_entropy) or (
                ent == best_entropy and is_cand and not best_is_candidate
            ):
                best_word = word
                best_entropy = ent
                best_is_candidate = is_cand

        return best_word


# ---------------------------------------------------------------------------
# Trajectory generation  (benchmark-compatible output)
# ---------------------------------------------------------------------------


def result_to_benchmark_dict(result: SolverResult, game_id: str) -> Dict[str, Any]:
    """Convert a ``SolverResult`` into a dict matching the benchmark JSON
    format (see ``GameBenchmark._save_results`` in ``src/benchmark.py``)."""
    return {
        "game_id": game_id,
        "status": "won" if result.won else "lost",
        "won": result.won,
        "total_moves": result.total_moves,
        "target": result.target,
        "duration_seconds": result.duration_seconds,
        "moves": [
            {
                "move_number": m.move_number,
                "player_input": f"Ответ: {m.guess}",
                "feedback": m.feedback_text,
                "is_valid": True,
                "metadata": {
                    "candidates_before": m.candidates_before,
                    "candidates_after": m.candidates_after,
                },
            }
            for m in result.moves
        ],
    }


def generate_trajectories(
    words: List[str],
    targets: List[str],
    max_attempts: int = 6,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate full trajectories for every word in *targets* and optionally
    save to a JSON file compatible with the benchmark format.

    Returns the full results dictionary.
    """
    solver = WordleSolver(words, max_attempts=max_attempts)

    game_results: List[Dict[str, Any]] = []
    wins = 0
    total_attempts = 0
    won_attempts = 0
    attempts_distribution: Counter = Counter()

    total_start = time.time()

    for idx, target in enumerate(targets, 1):
        result = solver.solve(target)
        game_dict = result_to_benchmark_dict(result, f"wordle_{idx}")
        game_results.append(game_dict)

        total_attempts += result.total_moves
        if result.won:
            wins += 1
            won_attempts += result.total_moves
            attempts_distribution[str(result.total_moves)] += 1
        else:
            attempts_distribution["failed"] += 1

        if idx % 100 == 0 or idx == len(targets):
            print(
                f"  [{idx}/{len(targets)}] win_rate={wins / idx:.3f}  "
                f"avg_attempts={total_attempts / idx:.2f}"
            )

    total_duration = time.time() - total_start
    n = len(targets)

    statistics = {
        "model_name": "heuristic_entropy",
        "game_type": "wordle",
        "total_games": n,
        "wins": wins,
        "losses": n - wins,
        "win_rate": wins / n if n else 0,
        "avg_attempts": total_attempts / n if n else 0,
        "avg_attempts_won": won_attempts / wins if wins else 0,
        "median_attempts": _median_attempts(game_results),
        "min_attempts": min(r["total_moves"] for r in game_results) if game_results else 0,
        "max_attempts": max(r["total_moves"] for r in game_results) if game_results else 0,
        "invalid_moves_total": 0,
        "attempts_distribution": dict(attempts_distribution),
        "total_duration_seconds": total_duration,
        "avg_duration_seconds": total_duration / n if n else 0,
    }

    output = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "model_name": "heuristic_entropy",
            "game_type": "wordle",
            "algorithm": "entropy_maximization",
        },
        "statistics": statistics,
        "games": game_results,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_path}")

    return output


def _median_attempts(games: List[Dict]) -> int:
    attempts = sorted(g["total_moves"] for g in games)
    n = len(attempts)
    if n == 0:
        return 0
    mid = n // 2
    if n % 2 == 1:
        return attempts[mid]
    return (attempts[mid - 1] + attempts[mid]) // 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Algorithmic Wordle solver (entropy heuristic)"
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Single target word to solve (prints trajectory to stdout)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate trajectories for ALL words in the dataset",
    )
    parser.add_argument(
        "--num-games",
        type=int,
        default=None,
        help="Number of games to play (random sample from dataset)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=6,
        help="Maximum guesses per game (default: 6)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=DEFAULT_DATASET,
        help="Path to a published wordle_*.jsonl dataset or legacy CSV",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (benchmark-compatible format)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for sampling (used with --num-games)",
    )

    args = parser.parse_args()

    words = load_words(args.dataset)
    print(f"Loaded {len(words)} words from {args.dataset}")

    # --- Single target mode ---
    if args.target:
        target = args.target.lower().replace("ё", "е")
        if target not in words:
            print(f"WARNING: '{target}' is not in the dataset; solving anyway.")
        solver = WordleSolver(words, max_attempts=args.max_attempts)
        result = solver.solve(target)
        _print_trajectory(result)
        if args.output:
            output = {
                "metadata": {
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "model_name": "heuristic_entropy",
                    "game_type": "wordle",
                },
                "games": [result_to_benchmark_dict(result, "wordle_1")],
            }
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"\nSaved to {args.output}")
        return

    # --- Multi-target modes ---
    if args.all:
        targets = words
    elif args.num_games:
        if args.seed is not None:
            random.seed(args.seed)
        targets = random.sample(words, min(args.num_games, len(words)))
    else:
        parser.print_help()
        return

    output_path = args.output or f"results/heuristic_wordle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    generate_trajectories(
        words, targets, max_attempts=args.max_attempts, output_path=output_path
    )


def _print_trajectory(result: SolverResult) -> None:
    """Pretty-print a single game trajectory to stdout."""
    status = "WON" if result.won else "LOST"
    print(f"\n{'=' * 50}")
    print(f"Target: {result.target}  |  Status: {status}  |  Moves: {result.total_moves}")
    print(f"Duration: {result.duration_seconds:.3f}s")
    print(f"{'=' * 50}")

    for m in result.moves:
        pattern_str = " ".join(FEEDBACK_NAMES[c] for c in m.feedback_pattern)
        print(f"\n  Move {m.move_number}: {m.guess}  →  [{pattern_str}]")
        print(f"    Candidates: {m.candidates_before} → {m.candidates_after}")

    print()


if __name__ == "__main__":
    main()
