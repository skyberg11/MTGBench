import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ONSET_CONSONANTS_EN = ['b', 'd', 'f', 'g', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'z',
                       'br', 'dr', 'fr', 'gr', 'kr', 'pr', 'tr', 'bl', 'fl', 'gl', 'pl', 'sl']
CODA_CONSONANTS_EN = ['b', 'd', 'f', 'g', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'z']
VOWELS_EN = ['a', 'e', 'i', 'o', 'u', 'ai', 'ea', 'ie', 'oo', 'ou']

ONSET_CONSONANTS_RU = ['б', 'в', 'г', 'д', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'з',
                       'бр', 'др', 'гр', 'кр', 'пр', 'тр', 'бл', 'фл', 'гл', 'пл', 'сл']
CODA_CONSONANTS_RU = ['б', 'в', 'г', 'д', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'з']
VOWELS_RU = ['а', 'е', 'и', 'о', 'у', 'ы', 'э', 'ю', 'я', 'ай', 'ей', 'ой']

SYLLABLE_PATTERNS_EN = [
    (['C', 'V'], 3),
    (['C', 'V', 'C'], 2),
    (['C', 'V', 'C', 'C'], 1),
]

SYLLABLE_PATTERNS_RU = [
    (['C', 'V'], 3),
    (['C', 'V', 'C'], 1),
]

RU_PREFIXES = [
    'при', 'от', 'пере', 'вы', 'за', 'под', 'раз', 'с', 'на', 'у',
    'про', 'до', 'о', 'об', 'вз', 'воз', 'из', 'пред', 'в', 'во',
    'пре', 'недо', 'ис', 'рас', 'вос', 'низ', 'нис', 'чрез', 'черес'
]

RU_NOUN_SUFFIXES = [
    'ник', 'тель', 'ость', 'ение', 'ание', 'ка', 'ица', 'ство',
    'ация', 'изм', 'ант', 'ор', 'ёр', 'ист', 'ёнок', 'чик', 'щик',
    'от', 'ет', 'изн', 'ин', 'ун', 'ак', 'як', 'арь', 'ырь'
]

RU_VERB_SUFFIXES = [
    'ать', 'ить', 'овать', 'евать', 'ивать', 'ывать', 'нуть',
    'еть', 'ать', 'ять', 'ти', 'чь', 'ну'
]

RU_ADJ_SUFFIXES = [
    'ный', 'ской', 'ий', 'ов', 'ев', 'ин', 'н', 'енн',
    'ист', 'ат', 'лив', 'чив', 'к', 'ск', 'оват', 'еват'
]

RU_ALL_SUFFIXES = RU_NOUN_SUFFIXES + RU_VERB_SUFFIXES + RU_ADJ_SUFFIXES

EN_PREFIXES = [
    'pre', 'un', 're', 'de', 'dis', 'mis', 'over', 'under', 'out',
    'sub', 'super', 'trans', 'inter', 'anti', 'counter', 'fore', 'post'
]

EN_SUFFIXES = [
    'tion', 'ness', 'ment', 'ship', 'hood', 'ism', 'ist', 'er', 'or',
    'able', 'ible', 'ful', 'less', 'ous', 'ive', 'al', 'ic', 'ly',
    'ing', 'ed', 'en', 'ize', 'ise', 'ify', 'ate', 'ent', 'ant'
]


def get_phonetics(language: str):
    if language == "ru":
        return ONSET_CONSONANTS_RU, CODA_CONSONANTS_RU, VOWELS_RU
    else:
        return ONSET_CONSONANTS_EN, CODA_CONSONANTS_EN, VOWELS_EN


def generate_syllable(seed: int, language: str = "en") -> str:
    random.seed(seed)
    onset_consonants, coda_consonants, vowels = get_phonetics(language)
    patterns_with_weights = SYLLABLE_PATTERNS_RU if language == "ru" else SYLLABLE_PATTERNS_EN
    patterns = [p for p, _ in patterns_with_weights]
    weights = [w for _, w in patterns_with_weights]
    pattern = random.choices(patterns, weights=weights, k=1)[0]
    syllable = ""
    first_c = True
    for char_type in pattern:
        if char_type == 'C':
            if first_c:
                syllable += random.choice(onset_consonants)
                first_c = False
            else:
                syllable += random.choice(coda_consonants)
        else:
            syllable += random.choice(vowels)
    return syllable


def generate_morphological_root(seed: int, language: str = "en",
                                min_syllables: int = 1, max_syllables: int = 2) -> str:
    random.seed(seed)
    syllable_options = list(range(min_syllables, max_syllables + 1))
    weights = [1.0 / (i + 1) for i in range(len(syllable_options))]
    num_syllables = random.choices(syllable_options, weights=weights, k=1)[0]
    root = ""
    for i in range(num_syllables):
        syllable_seed = seed * 100 + i
        root += generate_syllable(syllable_seed, language)
    return root


def generate_morphological_word(word_id: int, language: str = "en",
                                use_prefix: bool = None, use_suffix: bool = None) -> str:
    random.seed(word_id)
    if language == "ru":
        prefixes = RU_PREFIXES
        suffixes = RU_ALL_SUFFIXES
    else:
        prefixes = EN_PREFIXES
        suffixes = EN_SUFFIXES

    if use_prefix is None and use_suffix is None:
        r = random.random()
        if r < 0.7:
            use_prefix, use_suffix = False, True
        elif r < 0.9:
            use_prefix, use_suffix = True, False
        else:
            use_prefix, use_suffix = True, True

    if use_prefix is None:
        use_prefix = random.random() < 0.15
    if use_suffix is None:
        use_suffix = random.random() < 0.7

    parts = []
    if use_prefix:
        parts.append(random.choice(prefixes))

    root_seed = word_id * 10000
    root = generate_morphological_root(root_seed, language, min_syllables=1, max_syllables=2)
    parts.append(root)

    if use_suffix:
        parts.append(random.choice(suffixes))

    return ''.join(parts)


def generate_word(word_id: int, num_syllables: int = None, language: str = "en",
                  use_morphology: bool = True) -> str:
    if use_morphology:
        return generate_morphological_word(word_id, language)

    random.seed(word_id)
    if num_syllables is None:
        num_syllables = random.randint(2, 4)

    syllables = []
    for i in range(num_syllables):
        syllable_seed = word_id * 1000 + i
        syllables.append(generate_syllable(syllable_seed, language))

    return ''.join(syllables)


def generate_attribute_hierarchy(num_attributes: int, seed: int = 42,
                                 language: str = "en") -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    random.seed(seed)

    root_categories = []
    mid_level_attrs = []
    leaf_attrs = []
    attribute_levels = {}

    for i in range(5):
        attr_id = 1000000 + i
        attr_name = generate_morphological_word(attr_id, language, use_prefix=True, use_suffix=True)
        root_categories.append(attr_name)
        attribute_levels[attr_name] = 'root'

    attribute_hierarchy = {}
    for root in root_categories:
        attribute_hierarchy[root] = []

    num_mid_level = num_attributes // 3
    for i in range(num_mid_level):
        attr_id = 2000000 + i
        attr_name = generate_morphological_word(attr_id, language, use_prefix=True, use_suffix=True)
        parent = random.choice(root_categories)
        attribute_hierarchy[attr_name] = [parent]
        mid_level_attrs.append(attr_name)
        attribute_levels[attr_name] = 'mid'

    num_leaf = num_attributes - len(root_categories) - len(mid_level_attrs)
    for i in range(num_leaf):
        attr_id = 3000000 + i
        attr_name = generate_morphological_word(attr_id, language, use_prefix=True, use_suffix=True)

        num_parents = random.randint(1, min(3, len(mid_level_attrs)))
        parents = random.sample(mid_level_attrs, num_parents) if mid_level_attrs else [random.choice(root_categories)]

        all_parents = set(parents)
        for parent in parents:
            all_parents.update(attribute_hierarchy.get(parent, []))

        attribute_hierarchy[attr_name] = sorted(list(all_parents))
        leaf_attrs.append(attr_name)
        attribute_levels[attr_name] = 'leaf'

    return attribute_hierarchy, attribute_levels


def assign_attributes_to_words(
    num_words: int,
    attribute_hierarchy: Dict[str, List[str]],
    attribute_levels: Dict[str, str],
    min_attributes: int = 7,
    max_attributes: int = 20,
    seed: int = 42,
    language: str = "en"
) -> Dict[str, List[str]]:
    random.seed(seed)

    leaf_attributes = [k for k, level in attribute_levels.items() if level == 'leaf']
    mid_attributes = [k for k, level in attribute_levels.items() if level == 'mid']

    words_to_attributes = {}
    used_attribute_sets = set()

    attempts = 0
    max_attempts = num_words * 100

    word_id = 0
    while len(words_to_attributes) < num_words and attempts < max_attempts:
        attempts += 1

        word = generate_word(word_id, language=language)
        word_id += 1

        num_leaf_attrs = random.randint(
            max(1, min_attributes // 3),
            min(len(leaf_attributes), max_attributes // 3)
        )
        selected_leaf = random.sample(leaf_attributes, num_leaf_attrs)

        num_mid_attrs = random.randint(1, min(3, len(mid_attributes)))
        selected_mid = random.sample(mid_attributes, num_mid_attrs)

        all_attributes = set(selected_leaf + selected_mid)
        for attr in sorted(all_attributes):
            all_attributes.update(attribute_hierarchy.get(attr, []))

        if len(all_attributes) < min_attributes:
            continue

        if len(all_attributes) > max_attributes:
            roots_in_set = sorted(a for a in all_attributes if attribute_levels.get(a) == 'root')
            others_in_set = sorted(a for a in all_attributes if attribute_levels.get(a) != 'root')
            num_to_keep = max_attributes - len(roots_in_set)
            if num_to_keep > 0:
                all_attributes = set(roots_in_set + random.sample(others_in_set, min(num_to_keep, len(others_in_set))))
            else:
                all_attributes = set(roots_in_set)

        attr_tuple = tuple(sorted(all_attributes))
        if attr_tuple in used_attribute_sets:
            continue

        used_attribute_sets.add(attr_tuple)
        words_to_attributes[word] = sorted(list(all_attributes))

    if len(words_to_attributes) < num_words:
        print(f"Warning: Could only generate {len(words_to_attributes)} unique words (requested {num_words})")

    return words_to_attributes


def generate_episodes(
    num_episodes: int,
    words_per_episode_range: Tuple[int, int] = (80, 100),
    num_attributes: int = 150,
    min_attributes_per_word: int = 5,
    max_attributes_per_word: int = 12,
    max_turns: int = 21,
    seed: int = 42,
    language: str = "en",
    exclude_words: Optional[Set[str]] = None,
) -> List[Dict]:
    random.seed(seed)

    print(f"Generating attribute hierarchy with {num_attributes} attributes in {language.upper()}...")
    attribute_hierarchy, attribute_levels = generate_attribute_hierarchy(num_attributes, seed=seed, language=language)

    max_words_needed = num_episodes * words_per_episode_range[1]
    if exclude_words:
        # Generate extra words to compensate for excluded ones
        max_words_needed += len(exclude_words)

    print(f"Generating {max_words_needed} synthetic words...")
    all_words_to_attributes = assign_attributes_to_words(
        num_words=max_words_needed,
        attribute_hierarchy=attribute_hierarchy,
        attribute_levels=attribute_levels,
        min_attributes=min_attributes_per_word,
        max_attributes=max_attributes_per_word,
        seed=seed,
        language=language
    )

    if exclude_words:
        all_words_to_attributes = {w: a for w, a in all_words_to_attributes.items()
                                   if w not in exclude_words}
        print(f"After excluding benchmark words: {len(all_words_to_attributes)} words remaining")

    episodes = []
    all_words = list(all_words_to_attributes.keys())
    word_index = 0

    print(f"Creating {num_episodes} episodes...")
    for episode_id in range(num_episodes):
        num_words = random.randint(*words_per_episode_range)

        episode_words = all_words[word_index:word_index + num_words]
        word_index += num_words

        words_to_hypernyms = {
            word: all_words_to_attributes[word]
            for word in episode_words
        }

        hypernym_counts = [len(attrs) for attrs in words_to_hypernyms.values()]

        episode = {
            "key": episode_id,
            "controller": {
                "max_num_words": words_per_episode_range[1],
                "num_words": len(episode_words),
                "min_num_hypernyms_per_word": min(hypernym_counts) if hypernym_counts else 0,
                "max_num_hypernyms_per_word": max(hypernym_counts) if hypernym_counts else 0,
                "words_to_hypernyms": words_to_hypernyms,
                "max_turns": max_turns
            },
            "user_simulator_cfg_str": "TwentyQuestionsRuleBasedUserSimulator"
        }

        episodes.append(episode)

        if (episode_id + 1) % 10 == 0:
            print(f"  Generated {episode_id + 1}/{num_episodes} episodes")

    return episodes


def save_episodes(episodes: List[Dict], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for episode in episodes:
            json.dump(episode, f, ensure_ascii=False)
            f.write('\n')
    print(f"\nSaved {len(episodes)} episodes to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic dataset for Twenty Questions Consistency task"
    )
    parser.add_argument("--num-episodes", type=int, default=400)
    parser.add_argument("--words-per-episode-min", type=int, default=80)
    parser.add_argument("--words-per-episode-max", type=int, default=100)
    parser.add_argument("--num-attributes", type=int, default=150)
    parser.add_argument("--min-attributes-per-word", type=int, default=5)
    parser.add_argument("--max-attributes-per-word", type=int, default=12)
    parser.add_argument("--max-turns", type=int, default=21)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str,
                        required=True, help="Output JSONL path for the newly generated episodes")
    parser.add_argument("--language", type=str, default="ru", choices=["en", "ru"])
    args = parser.parse_args()

    output_file = Path(args.output)

    print(f"Configuration:")
    print(f"  Episodes: {args.num_episodes}")
    print(f"  Words per episode: {args.words_per_episode_min}-{args.words_per_episode_max}")
    print(f"  Total attributes: {args.num_attributes}")
    print(f"  Attributes per word: {args.min_attributes_per_word}-{args.max_attributes_per_word}")
    print(f"  Max turns: {args.max_turns}")
    print(f"  Random seed: {args.seed}")
    print(f"  Output: {output_file}")

    episodes = generate_episodes(
        num_episodes=args.num_episodes,
        words_per_episode_range=(args.words_per_episode_min, args.words_per_episode_max),
        num_attributes=args.num_attributes,
        min_attributes_per_word=args.min_attributes_per_word,
        max_attributes_per_word=args.max_attributes_per_word,
        max_turns=args.max_turns,
        seed=args.seed,
        language=args.language
    )

    save_episodes(episodes, output_file)
    print("Dataset generation complete!")


if __name__ == "__main__":
    main()
