import json
import os
import re
from typing import List, Dict
import random
import pandas as pd
import string
from pathlib import Path
import pickle

PROFICIENCY_LEVELS = ['A2', 'B1', 'B2', 'C1', 'C2']


def _resolve_dataset_path(filename: str, game: str) -> str:
    """Resolve a bare filename under the game's data directory; keep explicit paths."""
    if os.path.isabs(filename) or os.path.dirname(filename):
        return os.fspath(filename)
    return str(Path(__file__).resolve().parent / "datasets" / game / filename)


def load_jsonl_file(filepath: str) -> List[Dict]:
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def parse_json_content(content):
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        json_str = content[start: end + 1]
        return json.loads(json_str)


def parse_json_content_dict(content):
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        json_str = content[start: end + 1]
        return json.loads(json_str)


def load_word_list(table):
    with open(table, "r", encoding="utf-8") as f:
        words = [json.loads(line)["word"] for line in f]
    return words


def load_cities_list(table, all_cities_table, allowed_cities_table):
    """
    Load cities from YT table
    """
    with open(table, "r", encoding="utf-8") as f:
        cities = [json.loads(line)["city"] for line in f]
    with open(all_cities_table, 'r', encoding='utf-8') as f:
        all_cities = [json.loads(line)["city"] for line in f]
    with open(allowed_cities_table, 'r', encoding='utf-8') as f:
        allowed_cities = [json.loads(line)["city"] for line in f]
    return cities, all_cities, allowed_cities


def load_danetki(table: str):
    with open(table, "r", encoding="utf-8") as f:
        danetkas = [json.loads(line) for line in f]

    cleaned = []
    for p in danetkas:
        cleaned.append({
            "setup": p["setup"],
            "solution": p["solution"],
            "key_fact": p["key_fact"],
        })
    return cleaned


def load_episodes_twenty_questions(filename: str = None) -> List[Dict]:

    filepath = _resolve_dataset_path(filename, "twenty_questions_consistency")
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Twenty Questions episode file not found: {filepath}\n"
            f"Make sure the dataset file exists."
        )

    print(f"Loading Twenty Questions episodes from: {filepath}")

    if filepath.endswith('.jsonl'):
        data = load_jsonl_file(filepath)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                data = data.get("episodes", data)

    print(f"Loaded {len(data)} episodes")
    return data


def load_episodes_field_of_miracles(
    filename: str,
    episodes_per_level: int = 50,
    seed: int = 42,
) -> Dict[str, List[Dict]]:
    """
        Load or generate episodes split by proficiency level.

        Args:
            language: Language code
            episodes_per_level: Number of episodes per level
            dataset_type: Type of dataset to use ("proficiency" or "letter_difficulty")
        Returns:
        Dictionary mapping level to episodes
    """
    dataset_path = _resolve_dataset_path(filename, "wheel_of_fortune")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(
            f"Field of Miracles dataset not found at: {dataset_path}\n"
            f"Make sure the dataset file exists."
        )

    print(f"Loading words from Field of Miracles dataset: {dataset_path}")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and "words" in data:
        words = data["words"]
    elif isinstance(data, list):
        words = data
    else:
        raise ValueError("Unexpected dataset format. Expected dict with 'words' key or list of words.")

    print(f"   Loaded {len(words)} words")

    episodes_by_level = {level: [] for level in PROFICIENCY_LEVELS}

    for word_dict in words:
        level = word_dict.get("level", "A2")
        if level in episodes_by_level:
            episodes_by_level[level].append(word_dict)

    if seed is not None:
        random.seed(seed)
        print(f"Using random seed: {seed}")

    for level in PROFICIENCY_LEVELS:
        available = episodes_by_level[level]
        if len(available) > episodes_per_level:
            episodes_by_level[level] = random.sample(available, episodes_per_level)

    print(f"\nWords sampled by level:")
    for level in PROFICIENCY_LEVELS:
        count = len(episodes_by_level[level])
        print(f"   {level}: {count} words")

    return episodes_by_level


def load_words_descrs_from_pickle(filepath: str) -> Dict[str, Dict[str, str]]:
    """Load word features dictionary from pickle file."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Word features file not found: {filepath}")
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


def normalize_string(text: str) -> str:
    return text.translate(str.maketrans('', '', string.punctuation)).strip().lower()
