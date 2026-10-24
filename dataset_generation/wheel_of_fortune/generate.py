from pathlib import Path
import argparse
import csv
import json
from typing import Dict, List
import nltk
from nltk.corpus import brown, wordnet
from collections import Counter

from dataset_generation.wheel_of_fortune.freq_dict import freq_dict_path
from multiturn_games_benchmark.constants import (
    RUSSIAN_LETTER_FREQUENCY,
    ENGLISH_LETTER_FREQUENCY,
)


def get_letter_rarity_scores(language: str = "ru") -> Dict[str, float]:
    """Return {letter: 100 - freq} dict for the given language."""
    freqs = RUSSIAN_LETTER_FREQUENCY if language == "ru" else ENGLISH_LETTER_FREQUENCY
    return {letter: 100 - freq for letter, freq in freqs.items()}


LETTER_RARITY_SCORE = get_letter_rarity_scores("ru")
LEVELS = ["A2", "B1", "B2", "C1", "C2"]

def calculate_word_difficulty(word: str, language: str = "ru") -> float:
    """Calculate difficulty score based on average letter rarity. Higher = harder."""
    rarity = get_letter_rarity_scores(language)
    word_upper = word.upper()
    # Sorted, so the float sum (and the 2-dp rounding of .xx5 ties) is the same on every run.
    unique_letters = sorted(set(word_upper))
    scores = [rarity.get(letter, 50) for letter in unique_letters]
    if not scores:
        return 50.0
    return sum(scores) / len(scores)


def assign_difficulty_level(score: float, language: str = "ru") -> str:
    """Assign difficulty level based on score."""
    if language == "en":
        thresholds = (93.1, 93.6, 94.1, 94.6)
    else:
        thresholds = (94.0, 94.4, 94.8, 95.3)

    if score < thresholds[0]:
        return LEVELS[0]
    elif score < thresholds[1]:
        return LEVELS[1]
    elif score < thresholds[2]:
        return LEVELS[2]
    elif score < thresholds[3]:
        return LEVELS[3]
    else:
        return LEVELS[4]


def create_dataset(
        words: List[str],
        output_path: str,
        target_per_level: int = 250,
        language: str = "ru",
) -> Dict[str, List[Dict]]:
    """Create dataset with difficulty levels based on letter rarity."""

    word_data = []
    for word in words:
        score = calculate_word_difficulty(word, language=language)
        level = assign_difficulty_level(score, language=language)
        word_data.append({
            "word": word,
            "difficulty_score": round(score, 2),
            "level": level,
            "length": len(word),
        })

    by_level = dict((level, []) for level in LEVELS)
    for item in word_data:
        by_level[item["level"]].append(item)

    for level in by_level:
        by_level[level].sort(key=lambda x: x["difficulty_score"])

    dataset = {}
    for level in LEVELS:
        available = by_level[level]
        if level in LEVELS[:2]:
            dataset[level] = available[:target_per_level]
        else:
            dataset[level] = available[-target_per_level:] if len(available) >= target_per_level else available

    all_words = []
    for level in LEVELS:
        all_words.extend(dataset[level])

    if language == "en":
        metadata = {
            "source": "nltk_brown_corpus",
            "scoring_method": "letter_rarity",
            "total_words": len(all_words),
        }
    else:
        metadata = {
            "source": "freq_dict_ruslang.csv",
            "cite": "О. Н. Ляшевская, С. А. Шаров, Частотный словарь современного русского языка (на материалах Национального корпуса русского языка). М.: Азбуковник, 2009.",
            "scoring_method": "letter_rarity",
            "total_words": len(all_words),
        }

    output = {
        "metadata": metadata,
        "words": all_words,
    }

    save_json(output, output_path)

    print(f"\nCreated dataset: {output_path}")
    print(f"\nDistribution:")
    for level in LEVELS:
        count = len(dataset[level])
        if dataset[level]:
            min_score = min(w["difficulty_score"] for w in dataset[level])
            max_score = max(w["difficulty_score"] for w in dataset[level])
            print(f"  {level}: {count:3d} words (score range: {min_score:.2f} - {max_score:.2f})")

    return dataset


def load_words_from_nltk(min_length: int = 5, max_length: int = 29, nouns_only: bool = True,
                         require_definition: bool = True) -> List[str]:
    """Load English words from NLTK's Brown corpus, optionally filtering to nouns via WordNet.

    Args:
        require_definition: If True, keep only words that have at least one WordNet synset.
            This filters out rare/obscure words without known definitions.

    Returns list of lowercase words sorted by frequency (most frequent first).
    """

    nltk.download("brown", quiet=True)
    nltk.download("wordnet", quiet=True)

    word_freq = Counter()
    for word in brown.words():
        w = word.lower()
        if not w.isascii() or not w.isalpha():
            continue
        if not (min_length <= len(w) <= max_length):
            continue
        if w[0].isupper():
            continue
        word_freq[w] += 1

    words = list(word_freq.keys())

    if nouns_only:
        words = [w for w in words if wordnet.synsets(w, pos=wordnet.NOUN)]
    if require_definition:
        words = [w for w in words if wordnet.synsets(w) and wordnet.synsets(w)[0].definition()]

    words.sort(key=lambda w: word_freq[w], reverse=True)
    words = words[:10000]
    return words


def main():
    parser = argparse.ArgumentParser(description="Create letter-difficulty based dataset for Field of Miracles")
    parser.add_argument("--input", type=str, default=None,
                        help="Path to input word list (CSV from freq dict or plain text)")
    parser.add_argument("--output", type=str, required=True,
                        help="Path to output JSON file")
    parser.add_argument("--words-per-level", type=int, default=250,
                        help="Target number of words per difficulty level")
    parser.add_argument("--min-length", type=int, default=5, help="Minimum word length")
    parser.add_argument("--max-length", type=int, default=29, help="Maximum word length")
    parser.add_argument("--nouns-only", action="store_true",
                        help="Filter to keep only nouns (uses POS column for CSV input, WordNet for English)")
    parser.add_argument("--language", type=str, choices=["ru", "en"], default="ru",
                        help="Language for dataset generation")
    args = parser.parse_args()

    if args.language == "en" and args.input is None:
        print("Loading English words from NLTK Brown corpus...")
        words = load_words_from_nltk(args.min_length, args.max_length, nouns_only=args.nouns_only)
    else:
        input_path = args.input or freq_dict_path()
        print(f"Loading words from: {input_path}")
        pos_filter = 's' if args.nouns_only else None
        words = load_words_from_freq_csv(input_path, args.min_length, args.max_length,
                                         pos_filter=pos_filter)

    print(f"  Loaded {len(words)} words (length {args.min_length}-{args.max_length})")
    print(f"\nCreating dataset with {args.words_per_level} words per level...")
    create_dataset(
        words=words,
        output_path=args.output,
        target_per_level=args.words_per_level,
        language=args.language,
    )


def load_words_from_freq_csv(file_path: str, min_length: int = 5, max_length: int = 15,
                             pos_filter: str = None) -> List[str]:
    """Load words from freq_dict_ruslang.csv, filtering by length and optionally POS.

    Args:
        file_path: Path to CSV with columns: rank, lemma, pos, freq_ipm, ...
        min_length: Minimum word length
        max_length: Maximum word length
        pos_filter: If set, keep only this POS tag (e.g. 's' for nouns)
    """
    words = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['lemma'].strip()
            if pos_filter and row['pos'].strip() != pos_filter:
                continue
            if not (min_length <= len(word) <= max_length):
                continue
            if all(ord('а') <= ord(c.lower()) <= ord('я') or c.lower() == 'ё' for c in word):
                words.append(word)
    return words


def save_json(data, output_path: str) -> None:
    """Save data as JSON with utf-8 encoding."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
