"""Human sessions: majority outcome and rounded mean turns per target."""

import json
from collections import defaultdict

from .scoring import GAMES


def load_human_results(root):
    groups = defaultdict(list)
    sessions = 0
    for game in GAMES:
        for path in sorted(
            (root / "results/human_benchmark" / game).glob("*_results.json")
        ):
            if path.name.startswith(
                "._"
            ):  # macOS resource forks, not JSON trajectories
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data["games"]:
                if item["status"] not in {"won", "lost"}:
                    raise ValueError(f"Unexpected unfinished human session: {path}")
                target = item["target"]
                groups[(game, target)].append(item)
                sessions += 1
    episodes = []
    for (game, target), items in sorted(groups.items()):
        won = sum(item["won"] for item in items) / len(items) >= 0.5
        episodes.append(
            {
                "game": game,
                "model": "human",
                "mode": "answer_only",
                "language": "ru",
                "id": f"human_{game}_{len(episodes) + 1}",
                "target": target,
                "won": won,
                "status": "won" if won else "lost",
                "turns": round(sum(item["total_moves"] for item in items) / len(items)),
                "source": "results/human_benchmark",
                "sessions": len(items),
                # The Wordle and Wheel of Fortune figures replay individual sessions.
                **(
                    {f"{game}_sessions": items}
                    if game in {"wordle", "wheel_of_fortune"}
                    else {}
                ),
            }
        )
    return episodes, sessions
