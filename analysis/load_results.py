"""Read public schema 1.0; report interruptions and missing scheduled episodes."""

import json

from .scoring import GAMES


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_baselines(root):
    return {
        (lang, row["word"].lower().replace("ё", "е")): row["moves"]
        for lang in ("en", "ru")
        for row in read_jsonl(root / f"results/baselines/wordle/{lang}_baseline.jsonl")
    }


def load_llm_results(root, expected_episodes=100):
    episodes, excluded, repairs = [], [], []
    for game in GAMES:
        paths = sorted((root / "results" / game).glob("*/*.json"))
        if not paths:
            raise ValueError(f"No result files for {game}")
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema_version") != "1.0" or data.get("game") != game:
                raise ValueError(f"Unexpected result schema: {path}")
            meta = {key: data[key] for key in ("game", "model", "language", "mode")}
            if meta["language"] not in {"en", "ru"} or meta["mode"] not in {
                "answer_only",
                "cot",
                "reasoning",
            }:
                raise ValueError(f"Invalid condition: {path}")
            if (
                path.parent.name != meta["model"]
                or path.stem != f"{meta['language']}_{meta['mode']}"
            ):
                raise ValueError(f"Path and metadata disagree: {path}")
            source = str(path.relative_to(root))
            ids = set()
            for item in data["episodes"]:
                if item["id"] in ids:
                    raise ValueError(f"Duplicate episode {source}: {item['id']}")
                ids.add(item["id"])
                e = {**item, **meta, "source": source}
                if (
                    type(e["won"]) is not bool
                    or type(e["turns"]) is not int
                    or e["turns"] < 0
                ):
                    raise ValueError(f"Invalid outcome in {source}: {e['id']}")
                # The 20 Features runner historically left exhausted games in_progress.
                exhausted = (
                    game == "twenty_features"
                    and e["status"] == "in_progress"
                    and e["turns"] == 20
                    and not e["won"]
                )
                if e["status"] not in {"won", "lost"} and not exhausted:
                    excluded.append(
                        {
                            **meta,
                            "id": e["id"],
                            "source": source,
                            "reason": "incomplete",
                        }
                    )
                    continue
                if (e["status"] == "won") != e["won"]:
                    raise ValueError(
                        f"Inconsistent completed outcome: {source}: {e['id']}"
                    )
                if exhausted:
                    e["status"] = "lost"
                    repairs.append(
                        {
                            **meta,
                            "id": e["id"],
                            "reason": "20 Features exhausted its 20 features",
                        }
                    )
                if game == "wordle" and not e.get("target"):
                    # These releases omit target/prompt. IDs retain the original 100-word order.
                    words = read_jsonl(
                        root / f"multiturn_games_benchmark/datasets/wordle/wordle_{e['language']}.jsonl"
                    )
                    index = int(e["id"].removeprefix("wordle_")) - 1
                    if len(words) != 100 or not 0 <= index < len(words):
                        raise ValueError(f"Cannot restore target: {source}: {e['id']}")
                    e["target"] = words[index]["word"]
                    repairs.append(
                        {
                            **meta,
                            "id": e["id"],
                            "reason": "Wordle target restored from released dataset order",
                        }
                    )
                episodes.append(e)
            missing = expected_episodes - len(ids)
            if missing < 0:
                raise ValueError(f"More than {expected_episodes} episodes: {source}")
            for i in range(missing):
                excluded.append(
                    {
                        **meta,
                        "id": f"missing_{i + 1}",
                        "source": source,
                        "reason": "absent from released file",
                    }
                )
    return episodes, excluded, repairs
