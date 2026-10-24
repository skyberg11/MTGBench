#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main CLI entry point for multi-turn games benchmark"""

import argparse
import os
import random
import sys
from pathlib import Path
import pickle

# import truststore
# truststore.inject_into_ssl()

from multiturn_games_benchmark.benchmark import GameBenchmark
from multiturn_games_benchmark.config import Config
from multiturn_games_benchmark.games.cities_game import CitiesGame
from multiturn_games_benchmark.games.danetki_game import DanetkaGame
from multiturn_games_benchmark.games.field_of_miracles_game import FieldOfMiraclesGame
from multiturn_games_benchmark.games.twenty_questions_game import TwentyQuestionsGame
from multiturn_games_benchmark.games.wordle_game import WordleGame
from multiturn_games_benchmark.utils import (load_word_list, load_cities_list, load_danetki,
                       load_episodes_twenty_questions, load_episodes_field_of_miracles,
                       PROFICIENCY_LEVELS)
from multiturn_games_benchmark.games.twenty_features_game import TwentyFeaturesGame
from multiturn_games_benchmark.games.alias_game import AliasGame



def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Benchmark LLMs on multi-turn games",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'game',
        nargs='?',
        choices=['wordle', 'word_chain', 'situation_puzzles', 'twenty_questions', 'wheel_of_fortune', 'twenty_features', 'alias'],
        help='Type of game to benchmark'
    )

    parser.add_argument('--model', type=str, help='Model name from models.json')
    parser.add_argument('--table-path', type=str, help='Dataset file; dataset directory for Alias and 20 Features')
    parser.add_argument('--max-attempts', type=int, default=20, help='Turn limit; 20 Questions is fixed at 20 and Wheel of Fortune uses its language limit')
    parser.add_argument('--num-games', type=int, default=10, help='Requested episodes before --game-numbers filtering; Wheel of Fortune uses five equal groups')
    parser.add_argument('--seed', type=int, help='Seed for episode sampling and initial states, not API generation')
    parser.add_argument('--word_chain_path', type=str,
                        help='Path to all cities table')
    parser.add_argument('--word_chain_allowed', type=str,
                        help='Path to allowed cities table of a greedy selection')
    parser.add_argument('--CoT', action='store_true', default=False,
                        help='Enable CoT prompts; native reasoning is controlled by models.json')
    parser.add_argument('--language', type=str, choices=['ru', 'en'], default='ru',
                        help='Language for game prompts and dataset')
    parser.add_argument('--verifier', type=str, help='Judge model name for verifier from models.json')
    parser.add_argument('--game-numbers', type=str, default=None,
                        help='1-based positions after sampling, e.g. 3,52,99 (not permanent dataset IDs)')

    parser.add_argument('--enable_nei', type=str, help='Allow requesting another feature in 20 Features', choices=['true', 'false'], default='false')
    
    args = parser.parse_args()
    if not args.game or not args.model or not args.table_path:
        parser.error("game, --model and --table-path are required")
    if args.num_games < 1 or args.max_attempts < 1:
        parser.error("--num-games and --max-attempts must be positive")
    if args.game in {"situation_puzzles", "twenty_features", "alias"} and not args.verifier:
        parser.error(f"--verifier is required for {args.game}")
    if args.game == "word_chain" and not (args.word_chain_path and args.word_chain_allowed):
        parser.error("Word Chain requires --word_chain_path and --word_chain_allowed")
    if args.game == "wheel_of_fortune" and args.num_games < 5:
        parser.error("Wheel of Fortune needs at least 5 episodes (one per sampling stratum)")
    if args.game_numbers is not None:
        try:
            numbers = [int(n) for n in args.game_numbers.split(",")]
        except ValueError:
            parser.error("--game-numbers must be comma-separated positive integers")
        if not numbers or min(numbers) < 1:
            parser.error("--game-numbers uses positive, 1-based positions")
    return args


def run_wordle_benchmark(args, config: Config):
    """Run Wordle benchmark"""

    # Get model configuration
    model_config = config.get_model_config(args.model)

    # Validate model configuration
    try:
        config.validate_model_config(args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Loading words from {args.table_path}...")
    words = load_word_list(args.table_path)
    print(f"Found {len(words)} words")

    # Set random seed if specified
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    # Sample random words
    if len(words) <= args.num_games:
        print(f"Warning: Only {len(words)} words available, using all of them")
        target_words = words
    else:
        target_words = random.sample(words, args.num_games)

    # Create game instances
    games = []

    for i, word in enumerate(target_words):
        if args.game_numbers is not None and (i + 1) not in args.game_numbers:
            continue

        game = WordleGame(
            game_id=f"wordle_{i+1}",
            target_word=word,
            max_attempts=args.max_attempts,
            enable_reasoning=args.CoT,
            language=args.language
        )
        games.append(game)

    # Create and run benchmark
    benchmark = GameBenchmark(
        game_type='wordle',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        max_attempts=args.max_attempts,
        save_results=True
    )

    return benchmark.return_tokens()


def run_cities_benchmark(args, config: Config):
    """Run Cities benchmark for single model"""

    # Get model configuration
    model_config = config.get_model_config(args.model)

    # Validate model configuration
    try:
        config.validate_model_config(args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Load cities
    print(f"Loading cities from {args.table_path}...")
    cities, all_cities, allowed_cities = load_cities_list(args.table_path, args.word_chain_path, args.word_chain_allowed)
    print(f"Found {len(all_cities)} cities in total. Benchmarking on {len(cities)}. {len(allowed_cities)} is allowed")

    # Set random seed if specified
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    # Shuffle cities once for all games
    shuffled_cities = all_cities.copy()
    random.shuffle(shuffled_cities)

    if len(cities) <= args.num_games:
        print(f"Warning: Only {len(cities)} cities available, using all of them")
        target_words = cities
    else:
        target_words = random.sample(cities, args.num_games)

    # Create game instances
    games = []
    for i in range(len(target_words)):
        if args.game_numbers is not None and (i + 1) not in args.game_numbers:
            continue

        game = CitiesGame(
            game_id=f"cities_{i+1}",
            cities_list=shuffled_cities,
            allowed_cities_list = allowed_cities,
            start_city=target_words[i],
            max_attempts=args.max_attempts,
            enable_reasoning=args.CoT,
            language=args.language
        )
        games.append(game)

    # Create and run benchmark
    benchmark = GameBenchmark(
        game_type='cities',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        max_attempts=args.max_attempts,
        save_results=True
    )

    return benchmark.return_tokens()

# ==========================
# DANETKA
# ==========================


def run_danetka_benchmark(args, config: Config):
    """Run Danetka benchmark for single model (LLM-as-a-judge)"""

    # Get model configuration (будет использоваться как игрок)
    model_config = config.get_model_config(args.model)

    # Validate model configuration
    try:
        config.validate_model_config(args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Get judge model configuration if specified via CLI
    judge_model_config = None
    if args.verifier:
        try:
            judge_model_config = config.get_model_config(args.verifier)
            config.validate_model_config(args.verifier)
            print(f"Using judge model: {args.verifier}")
        except ValueError as e:
            print(f"Error with judge model: {e}")
            sys.exit(1)

    # Load danetki
    print(f"Loading danetki from {args.table_path}...")
    puzzles = load_danetki(args.table_path)
    print(f"Found {len(puzzles)} danetki")

    if not puzzles:
        print("Error: no danetki found in puzzles file")
        sys.exit(1)

    filtered = puzzles

    # Set random seed if specified
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    # Sample puzzles
    if len(filtered) <= args.num_games:
        print(f"Warning: Only {len(filtered)} puzzles available, using all of them")
        selected = filtered
    else:
        selected = random.sample(filtered, args.num_games)

    # Create game instances
    games = []
    for i, p in enumerate(selected):
        if args.game_numbers is not None and (i + 1) not in args.game_numbers:
            continue

        puzzle_dict = {
            "setup": p["setup"],
            "solution": p["solution"],
            "key_fact": p["key_fact"]
        }
        game = DanetkaGame(
            game_id=f"danetka_{i+1}",
            puzzle=puzzle_dict,
            max_attempts=args.max_attempts,
            enable_reasoning=args.CoT,
            language=args.language,
            judge_model_config=judge_model_config
        )
        games.append(game)

    # Create and run benchmark
    benchmark = GameBenchmark(
        game_type='danetka',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        max_attempts=args.max_attempts,
        save_results=True
    )

    return benchmark.return_tokens()


# ==========================
# TWENTY QUESTIONS
# ==========================


def run_twenty_questions_benchmark(args, config: Config):
    """Run Twenty Questions Consistency benchmark"""
    model_config = config.get_model_config(args.model)

    try:
        config.validate_model_config(args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Loading Twenty Questions episodes from {args.table_path}...")
    episodes = load_episodes_twenty_questions(filename=args.table_path)
    print(f"Found {len(episodes)} episodes")

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    random.shuffle(episodes)

    games = []
    for i in range(min(args.num_games, len(episodes))):
        if args.game_numbers is not None and (i + 1) not in args.game_numbers:
            continue

        episode = episodes[i]
        controller = episode["controller"]
        word_pool = list(controller["words_to_hypernyms"].keys())
        secret_word = random.choice(word_pool)

        game = TwentyQuestionsGame(
            game_id=f"twenty_q_{i+1}",
            word_pool=word_pool,
            word_attributes=controller["words_to_hypernyms"],
            max_attempts=20,
            enable_reasoning=args.CoT,
            language=args.language,
            fixed_secret_word=secret_word
        )
        games.append(game)

    benchmark = GameBenchmark(
        game_type='twenty_questions',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        save_results=True
    )
    return benchmark.return_tokens()


def run_field_of_miracles_benchmark(args, config: Config):
    """Run Field of Miracles benchmark"""
    model_config = config.get_model_config(args.model)

    try:
        config.validate_model_config(args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Loading Field of Miracles episodes from {args.table_path}...")
    episodes = load_episodes_field_of_miracles(
        filename=args.table_path,
        episodes_per_level=args.num_games // 5,
        seed=args.seed
    )

    games = []
    game_num = 0
    for level in PROFICIENCY_LEVELS:
        for episode in episodes[level]:
            game_num += 1
            if args.game_numbers is not None and game_num not in args.game_numbers:
                continue

            game = FieldOfMiraclesGame(
                game_id=f"field_of_miracles_{game_num}",
                word=episode['word'],
                enable_reasoning=args.CoT,
                language=args.language,
                level=level,
            )
            games.append(game)

    benchmark = GameBenchmark(
        game_type='field_of_miracles',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        save_results=True
    )
    return benchmark.return_tokens()


def run_twenty_features_benchmark(args, config: Config):
    model_config = config.get_model_config(args.model)

    print(f"Loading word features from {args.table_path}...")
    language = args.language
    file_mapping = {
        'en': 'words_descrs_shuffled_new_en',
        'ru': 'words_descrs_shuffled_new_ru',
    }
    pkl_prefix_path = Path(args.table_path)
    pkl_filepath = os.path.join(pkl_prefix_path, file_mapping[language])
    print(f"Loading word features from {pkl_filepath}...")
    if not pkl_prefix_path.exists():
        raise FileNotFoundError(f"Word features file not found: {pkl_filepath}")

    with open(pkl_filepath, 'rb') as f:
        word_features = pickle.load(f)
    print(f"Loaded {len(word_features)} from {pkl_filepath} words with features.")

    try:
        verifier_model_config = config.get_model_config(args.verifier)
    except ValueError:
        print("Warning: 'verifier' model not found in models.json. Using default...")
        sys.exit(1)

    words = list(word_features.keys())

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    random.shuffle(words)

    if len(words) <= args.num_games:
        print(f"Warning: Only {len(words)} words available, using all of them")
        target_words = words
    else:
        target_words = words[:args.num_games]

    games = []
    enable_nei = True if args.enable_nei == 'true' else False
    for i, word in enumerate(target_words):
        if args.game_numbers is not None and (i + 1) not in args.game_numbers:
            continue

        game = TwentyFeaturesGame(
            game_id=f"twenty_features_{i+1}",
            verifier_model_config=verifier_model_config,
            word_features=word_features,
            target_word=word,
            max_attempts=args.max_attempts,
            is_CoT=args.CoT,
            enable_nei=enable_nei,
            language=language
        )
        games.append(game)

    benchmark = GameBenchmark(
        game_type='twenty_features',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        save_results=True
    )
    return benchmark.return_tokens()


def run_alias_benchmark(args, config: Config):
    model_config = config.get_model_config(args.model)

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    persons_suffix = {
        'en': 'persons_en',
        'ru': 'persons_ru',
    }
    persons_path = Path(os.path.join(args.table_path, persons_suffix[args.language]))
    if not persons_path.exists():
        raise FileNotFoundError(f"Persons file not found: {persons_path}")
    with open(persons_path, 'rb') as f:
        persons_data = pickle.load(f)
        persons_data = [(category, name) for category, names in persons_data.items() for name in names]
        random.shuffle(persons_data)
    print(f"Loaded {len(persons_data)} persons.")

    try:
        verifier_model_config = config.get_model_config(args.verifier)
    except ValueError:
        print("Warning: 'verifier' model not found in models.json. Using default...")
        sys.exit(1)

    all_names = []
    for category, name in persons_data:
        target_name, file_name = name['target_name'], name['file_name']
        bio_path = os.path.join(
            args.table_path, 'Bio', category, args.language, file_name
        )
        all_names.append((target_name, str(bio_path)))

    if len(all_names) <= args.num_games:
        selected = all_names
    else:
        selected = all_names[:args.num_games]

    games = []
    for i, (name, bio_path) in enumerate(selected):
        if args.game_numbers is not None and (i + 1) not in args.game_numbers:
            continue

        game = AliasGame(
            game_id=f"alias_{i+1}",
            target_person=name,
            bio_path=bio_path,
            verifier_model_config=verifier_model_config,
            max_attempts=args.max_attempts,
            is_CoT=args.CoT,
            language=args.language
        )
        games.append(game)

    benchmark = GameBenchmark(
        game_type='alias',
        model_config=model_config
    )

    stats = benchmark.run_benchmark(
        games=games,
        save_results=True
    )
    return benchmark.return_tokens()

    
# ==========================
# MAIN
# ==========================

def main():
    """Main entry point"""
    args = parse_args()

    # Load configuration
    models_config_folder = Path(os.getenv("INPUT_SCRIPT_PATH", "."))
    try:
        config = Config(models_config_path=models_config_folder / "models.json")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Validate required arguments
    if not args.game:
        print("Error: game type is required (use --help to see available games)")
        sys.exit(1)

    if not args.model:
        print("Error: --model is required")
        print(f"Available models: {', '.join(config.list_available_models())}")
        sys.exit(1)

    if args.game_numbers is not None:
        numbers = args.game_numbers.strip().split(',')
        numbers = [int(n) for n in numbers]
        args.game_numbers = numbers

    if args.game == 'wordle':
        prompt_tokens, completion_tokens, cost = run_wordle_benchmark(args, config)
    elif args.game == 'word_chain':
        prompt_tokens, completion_tokens, cost = run_cities_benchmark(args, config)
    elif args.game == 'situation_puzzles':
        prompt_tokens, completion_tokens, cost = run_danetka_benchmark(args, config)
    elif args.game == 'twenty_questions':
        prompt_tokens, completion_tokens, cost = run_twenty_questions_benchmark(args, config)
    elif args.game == 'wheel_of_fortune':
        prompt_tokens, completion_tokens, cost = run_field_of_miracles_benchmark(args, config)
    elif args.game == 'twenty_features':
        prompt_tokens, completion_tokens, cost = run_twenty_features_benchmark(args, config)
    elif args.game == 'alias':
        prompt_tokens, completion_tokens, cost = run_alias_benchmark(args, config)
    else:
        raise ValueError(f"Unknown game type {args.game}")

    print('=================================')
    print('TOTAL TOKENS')
    print(f"Prompt tokens: {prompt_tokens}")
    print(f"Completion tokens: {completion_tokens}")
    print(f"COST (usd): {cost}")


if __name__ == '__main__':
    main()
