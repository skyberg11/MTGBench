import argparse
from pathlib import Path
from importlib.resources import files
import os
import json
import random
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from openai import OpenAI


base_url = "https://openrouter.ai/api/v1"


GENERATION_MODELS = [
    "google/gemini-2.5-pro-preview-03-25",
    "deepseek/deepseek-chat-v3-0324",
    "openai/gpt-5.1"
]

EMBEDDING_MODEL = "text-embedding-3-large"

EVAL_MODEL = "openai/gpt-5-mini-2025-08-07"

INPUT_PARAMS_PATH = "settings.json"
OUTPUT_PUZZLES_PATH = "puzzles.json"

NUM_PUZZLES = 300 
TARGET_PUZZLES = 150

GEN_TEMPERATURE = 1
EVAL_TEMPERATURE = 0



def create_client() -> OpenAI:
    return OpenAI(base_url=base_url, api_key=os.getenv("api_key_env") or os.getenv("TOKEN"))

def load_param_lists(path: str) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for key in ["genres", "topics", "settings", "twist_types"]:
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"JSON is missing a valid list for '{key}'")

    return data


def sample_param_combinations(param_lists: Dict[str, List[str]], n: int) -> List[Dict[str, str]]:
    genres = param_lists["genres"]
    topics = param_lists["topics"]
    settings = param_lists["settings"]
    twist_types = param_lists["twist_types"]

    combos = []
    for _ in range(n):
        combos.append(
            {
                "genre": random.choice(genres).strip(),
                "topic": random.choice(topics).strip(),
                "setting": random.choice(settings).strip(),
                "twist_type": random.choice(twist_types).strip(),
            }
        )
    return combos


# ==========================
# GENERATION OF PUZZLES
# ==========================

GEN_SYSTEM_PROMPT = files(__package__).joinpath("prompts", "gen_system_prompt.txt").read_text(encoding="utf-8")


def build_gen_user_prompt(params: Dict[str, str]) -> str:
    """
    IMPORTANT: we only use ONE random parameter from the four.
    The rest are not mentioned in the prompt.
    """
    key = random.choice(["genre", "topic", "setting", "twist_type"])

    if key == "genre":
        param_line = f"- Genre: {params['genre']}"
    elif key == "topic":
        param_line = f"- Topic: {params['topic']}"
    elif key == "setting":
        param_line = f"- Setting: {params['setting']}"
    else:  # "twist_type"
        param_line = f"- Twist type: {params['twist_type']}"

    return files(__package__).joinpath("prompts", "build_gen_user_prompt.txt").read_text(encoding="utf-8").format(value_0=param_line).strip()


def parse_json_content(content: str) -> Any:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"Could not find JSON in the model's response: {content}")
        json_str = content[start: end + 1]
        return json.loads(json_str)


def generate_puzzle(
    client: OpenAI,
    params: Dict[str, str],
    seed: int
) -> Dict[str, Any]:
    user_prompt = build_gen_user_prompt(params)
    generation_model = random.choice(GENERATION_MODELS)
    resp = client.chat.completions.create(
        model=generation_model,
        temperature=GEN_TEMPERATURE,
        seed=seed,
        messages=[
            {"role": "system", "content": GEN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    resp = resp.response
    content = resp['choices'][0]['message']['content']
    data = parse_json_content(content)

    return {
        "full_story": data.get("full_story", "").strip(),
        "setup": data.get("setup", "").strip(),
        "solution": data.get("solution", "").strip(),
        "key_fact": data.get("key_fact", "").strip(),
    }


# ==========================
# EVALUATION OF APPROPRIATENESS
# ==========================

EVAL_SYSTEM_PROMPT = files(__package__).joinpath("prompts", "eval_system_prompt.txt").read_text(encoding="utf-8")


def build_eval_user_prompt(sample: Dict[str, Any]) -> str:
    return files(__package__).joinpath("prompts", "build_eval_user_prompt.txt").read_text(encoding="utf-8").format(value_0=sample['setup'], value_1=sample['solution']).strip()


def evaluate_puzzle(
    client: OpenAI,
    sample: Dict[str, Any],
) -> Dict[str, Any]:
    user_prompt = build_eval_user_prompt(sample)
    resp = client.chat.completions.create(
        model=EVAL_MODEL,
        temperature=EVAL_TEMPERATURE,
        messages=[
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    resp = resp.response
    content = resp['choices'][0]['message']['content'].strip()
    data = parse_json_content(content)

    score = data.get("score")
    complexity = data.get("complexity")
    comment = data.get("comment", "").strip()
    return {
        "score": score,
        "score_comment": comment,
        "complexity": complexity
    }


# ==========================
# EMBEDDINGS AND SEMANTIC SELECTION
# ==========================

def get_embeddings(texts: List[str]) -> np.ndarray:
    from .generate_lists import get_embeddings as embed
    return embed(create_client(), texts, model=EMBEDDING_MODEL)


def cosine_distance_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    sim = np.dot(a_norm, b_norm.T)
    return 1.0 - sim


def farthest_point_sampling(embeddings: np.ndarray, k: int) -> List[int]:
    n = embeddings.shape[0]
    if k >= n:
        return list(range(n))

    first = random.randrange(n)
    selected = [first]

    distances = cosine_distance_matrix(embeddings, embeddings[[first], :])[:, 0]
    min_dist = distances

    while len(selected) < k:
        candidates = [
            (idx, d)
            for idx, d in enumerate(min_dist)
            if idx not in selected
        ]
        next_idx, _ = max(candidates, key=lambda x: x[1])
        selected.append(next_idx)

        new_dists = cosine_distance_matrix(
            embeddings, embeddings[[next_idx], :]
        )[:, 0]
        min_dist = np.minimum(min_dist, new_dists)

    return selected


def select_puzzle_indices_semantically(
    puzzles: List[Dict[str, Any]],
    target_k: int,
) -> List[int]:
    """
    Select indices of puzzles, evenly distributed in the semantic space.
    The embedding is built on setup+solution.
    """
    if not puzzles:
        return []

    texts = [
        f"Puzzle: {p['setup']}. Solution: {p['solution']}".strip()
        for p in puzzles
    ]
    embeddings = get_embeddings(texts)
    k = min(target_k, len(puzzles))
    indices = farthest_point_sampling(embeddings, k=k)
    return indices


# ==========================
# MAIN
# ==========================

def _gen_worker(idx: int, params: Dict[str, str], seed: int) -> Dict[str, Any]:
    client = create_client()
    sample = generate_puzzle(client, params, seed=seed)
    sample["id"] = idx
    return sample


def main():
    global base_url, GENERATION_MODELS, EVAL_MODEL, EMBEDDING_MODEL, INPUT_PARAMS_PATH, OUTPUT_PUZZLES_PATH, NUM_PUZZLES, TARGET_PUZZLES
    parser = argparse.ArgumentParser(description="Generate and filter situation puzzles (manual validation still required)", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("settings.json"), help="Attribute pools JSON")
    parser.add_argument("--output", type=Path, required=True, help="Destination for candidate puzzles")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-url", default=base_url)
    parser.add_argument("--models", nargs="+", default=GENERATION_MODELS)
    parser.add_argument("--eval-model", default=EVAL_MODEL)
    parser.add_argument("--embedding-model", default=EMBEDDING_MODEL, help="Embedding model ID supported by the configured API")
    parser.add_argument("--num-puzzles", type=int, default=NUM_PUZZLES)
    parser.add_argument("--target-puzzles", type=int, default=TARGET_PUZZLES)
    args = parser.parse_args()
    base_url, GENERATION_MODELS, EVAL_MODEL = args.base_url, args.models, args.eval_model
    EMBEDDING_MODEL = args.embedding_model
    INPUT_PARAMS_PATH, OUTPUT_PUZZLES_PATH = args.input, args.output
    NUM_PUZZLES, TARGET_PUZZLES = args.num_puzzles, args.target_puzzles
    args.output.parent.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    # 0. can regulate parallelism
    MAX_WORKERS = min(10, (os.cpu_count() or 8) * 4)
    client = create_client()

    # 1. read lists of genres/topics/settings/twist_types
    param_lists = load_param_lists(INPUT_PARAMS_PATH)

    # 2. generate NUM_PUZZLES parameter sets
    param_combos = sample_param_combinations(param_lists, NUM_PUZZLES)

    # 2.1 fix seeds to reproduce and without shared RNG in threads
    rng = random.Random(args.seed)
    seeds = [rng.randrange(0, 1000) for _ in range(NUM_PUZZLES)]

    # 3. generate raw puzzles in parallel
    raw_results: List[Dict[str, Any]] = [None] * NUM_PUZZLES  # to collect by id

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {
            ex.submit(_gen_worker, idx, params, seeds[idx]): idx
            for idx, params in enumerate(param_combos)
        }

        done = 0
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                sample = fut.result()
                raw_results[idx] = sample
            except Exception as e:
                # decide what to do: crash, retry, or save the error
                print(e)
                raw_results[idx] = {
                    "id": idx,
                    "full_story": "",
                    "setup": "",
                    "solution": "",
                    "key_fact": "",
                    "error": str(e),
                }
            done += 1
            if done % 10 == 0 or done == NUM_PUZZLES:
                print(f"[{done}/{NUM_PUZZLES}] Generation of puzzles...")

    print(f"Semantic selection of {TARGET_PUZZLES} puzzles from {len(raw_results)}...")
    selected_indices = select_puzzle_indices_semantically(raw_results, TARGET_PUZZLES)
    selected_results = [raw_results[i] for i in selected_indices]
    # 5. evaluate only selected puzzles
    for idx, sample in enumerate(selected_results):
        print(f"[{idx+1}/{len(selected_results)}] Evaluation of appropriateness...")
        eval_result = evaluate_puzzle(client, sample)
        sample.update(eval_result)

    # 6. write only selected puzzles to JSON
    out = {
        "puzzles": selected_results,
        "meta": {
            "generated_total": len(raw_results),
            "selected_count": len(selected_results),
        }
    }

    with open(OUTPUT_PUZZLES_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(
        f"Done. Generated {len(raw_results)} puzzles, "
        f"selected {len(out)} by semantic and saved to {OUTPUT_PUZZLES_PATH}"
    )


if __name__ == "__main__":
    main()
