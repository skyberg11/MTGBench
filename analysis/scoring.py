"""Episode scores: zero-based terminal turns, as in the paper appendix."""

GAMES = (
    "wordle",
    "word_chain",
    "situation_puzzles",
    "twenty_questions",
    "wheel_of_fortune",
    "twenty_features",
    "alias",
)
HORIZONS = {
    "wordle": 20,
    "word_chain": 25,
    "situation_puzzles": 20,
    "twenty_questions": 20,
    "wheel_of_fortune": 29,
    "twenty_features": 20,
    "alias": 30,
}


def letter_classes(word, language):
    """Canonical classes used by the Russian Wheel of Fortune environment."""
    table = (
        str.maketrans({"Й": "И", "Ё": "Е", "Ъ": "Ь", "Ы": "Ь"})
        if language == "ru"
        else {}
    )
    return word.upper().translate(table)


def score_episode(episode, wordle_baselines):
    game, turns, won = episode["game"], episode["turns"], episode["won"]
    if (
        game not in GAMES
        or type(won) is not bool
        or type(turns) is not int
        or turns < 0
        or (turns == 0 and not (game == "twenty_questions" and won))
    ):
        raise ValueError(f"Invalid scoring inputs: {game}, {turns}, {won}")
    if game in {"word_chain", "twenty_questions"}:
        return 1.0 if won else min(1.0, (turns - 1) / HORIZONS[game])
    if not won:
        return 0.0
    if game == "wordle":
        key = (episode["language"], episode["target"].lower().replace("ё", "е"))
        if key not in wordle_baselines:
            raise ValueError(f"Missing Wordle baseline for {key}")
        floor = (
            wordle_baselines[key] - 1
        )  # Convert the saved baseline turn count to an index.
    elif game == "wheel_of_fortune":
        floor = len(set(letter_classes(episode["target"], episode["language"]))) / 2
    else:
        floor = {"situation_puzzles": 1, "twenty_features": 2, "alias": 9}[game]
    horizon = HORIZONS[game]
    if not 0 <= floor < horizon:
        raise ValueError(f"Invalid scoring floor: {floor}")
    return max(0.0, min(1.0, 1 - (turns - 1 - floor) / (horizon - floor)))
