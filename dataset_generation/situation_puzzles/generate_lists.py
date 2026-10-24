import argparse
from pathlib import Path
from importlib.resources import files
import os
import json
import random
from typing import List

import numpy as np
from openai import OpenAI

# ==========================
# SETTINGS
# ==========================

base_url = "https://openrouter.ai/api/v1"

# Three different models for generation
GENERATION_MODELS = [
    "google/gemini-2.5-pro-preview-03-25",
    "deepseek/deepseek-chat-v3-0324",
    "openai/gpt-5-2025-08-07",
]

# Model for embeddings
EMBEDDING_MODEL = "text-embedding-3-large"

SAMPLES_PER_MODEL_PER_LIST = 50   # for each list (genre/topic/...) from each model
TARGET_COUNT_PER_LIST = 100       # how many to leave after semantic selection

TEMPERATURE = 1.3



# ==========================
# CLIENT
# ==========================
def create_client() -> OpenAI:
    return OpenAI(base_url=base_url, api_key=os.getenv("api_key_env") or os.getenv("TOKEN"))


# ==========================
# PROMPTS FOR EACH LIST
# ==========================

GENRE_SYSTEM_PROMPT = files(__package__).joinpath("prompts", "genre_system_prompt.txt").read_text(encoding="utf-8")

TOPIC_SYSTEM_PROMPT = files(__package__).joinpath("prompts", "topic_system_prompt.txt").read_text(encoding="utf-8")

SETTING_SYSTEM_PROMPT = files(__package__).joinpath("prompts", "setting_system_prompt.txt").read_text(encoding="utf-8")

TWIST_SYSTEM_PROMPT = files(__package__).joinpath("prompts", "twist_system_prompt.txt").read_text(encoding="utf-8")



def build_user_prompt_for_list(n: int, list_name: str) -> str:
    return files(__package__).joinpath("prompts", "build_user_prompt_for_list.txt").read_text(encoding="utf-8").format(value_0=n, value_1=list_name, value_2=n).strip()


# ==========================
# HELPER FUNCTIONS FOR LLM
# ==========================

def _parse_json_array_of_strings(content: str) -> List[str]:
    content = content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            raise ValueError(f"Could not find JSON array in the model's response: {content}")
        json_str = content[start: end + 1]
        data = json.loads(json_str)

    if not isinstance(data, list):
        raise ValueError("The model's response should be a JSON array.")
    result: List[str] = []
    for item in data:
        if isinstance(item, str):
            s = item.strip()
            if s:
                result.append(s)
    return result


def generate_list_with_model(
    client: OpenAI,
    model: str,
    system_prompt: str,
    list_name: str,
    n: int,
) -> List[str]:
    user_prompt = build_user_prompt_for_list(n, list_name)
    
    resp = client.chat.completions.create(
        model=model,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    resp = resp.response
    content = resp['choices'][0]['message']['content']
    return _parse_json_array_of_strings(content)


# ==========================
# EMBEDDINGS AND SEMANTIC SELECTION
# ==========================
def get_embeddings(client: OpenAI, texts: List[str], model: str = None) -> np.ndarray:
    response = client.embeddings.create(model=model or EMBEDDING_MODEL, input=texts)
    ordered = sorted(response.data, key=lambda item: item.index)
    if [item.index for item in ordered] != list(range(len(texts))):
        raise ValueError("Embedding response does not cover the requested texts")
    return np.asarray([item.embedding for item in ordered], dtype=np.float32)


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


def select_semantically_balanced(
    client: OpenAI,
    items: List[str],
    prefix: str,
    target_k: int,
) -> List[str]:
    if not items:
        return []

    # add prefix to make embeddings for different list types more meaningful
    texts = [f"{prefix}: {x}" for x in items]
    embeddings = get_embeddings(client, texts, model=EMBEDDING_MODEL)
    k = min(target_k, len(items))
    indices = farthest_point_sampling(embeddings, k=k)
    return [items[i] for i in indices]


# ==========================
# MAIN SCENARIO
# ==========================

def main():
    global base_url, GENERATION_MODELS, EMBEDDING_MODEL, SAMPLES_PER_MODEL_PER_LIST, TARGET_COUNT_PER_LIST
    parser = argparse.ArgumentParser(description="Generate and diversify situation-puzzle attribute pools", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON for generated pools")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-url", default=base_url)
    parser.add_argument("--models", nargs="+", default=GENERATION_MODELS)
    parser.add_argument("--embedding-model", default=EMBEDDING_MODEL)
    parser.add_argument("--samples-per-model", type=int, default=SAMPLES_PER_MODEL_PER_LIST)
    parser.add_argument("--target-count", type=int, default=TARGET_COUNT_PER_LIST)
    args = parser.parse_args()
    base_url, GENERATION_MODELS, EMBEDDING_MODEL = args.base_url, args.models, args.embedding_model
    SAMPLES_PER_MODEL_PER_LIST, TARGET_COUNT_PER_LIST = args.samples_per_model, args.target_count
    random.seed(args.seed)
    client = create_client()

    # -------- GENRES --------
    genre_items_all: List[str] = []
    for model in GENERATION_MODELS:
        vals = generate_list_with_model(
            client=client,
            model=model,
            system_prompt=GENRE_SYSTEM_PROMPT,
            list_name="genres",
            n=SAMPLES_PER_MODEL_PER_LIST,
        )
        genre_items_all.extend(vals)
    random.shuffle(genre_items_all)
    genres = select_semantically_balanced(
        client=client,
        items=genre_items_all,
        prefix="Genre",
        target_k=TARGET_COUNT_PER_LIST,
    )

    # -------- TOPICS --------
    topic_items_all: List[str] = []
    for model in GENERATION_MODELS:
        vals = generate_list_with_model(
            client=client,
            model=model,
            system_prompt=TOPIC_SYSTEM_PROMPT,
            list_name="topics",
            n=SAMPLES_PER_MODEL_PER_LIST,
        )
        topic_items_all.extend(vals)
    random.shuffle(topic_items_all)
    topics = select_semantically_balanced(
        client=client,
        items=topic_items_all,
        prefix="Topic",
        target_k=TARGET_COUNT_PER_LIST,
    )

    # -------- PLACES OF ACTION (SETTINGS) --------
    setting_items_all: List[str] = []
    for model in GENERATION_MODELS:
        vals = generate_list_with_model(
            client=client,
            model=model,
            system_prompt=SETTING_SYSTEM_PROMPT,
            list_name="places of action",
            n=SAMPLES_PER_MODEL_PER_LIST,
        )
        setting_items_all.extend(vals)
    random.shuffle(setting_items_all)
    settings = select_semantically_balanced(
        client=client,
        items=setting_items_all,
        prefix="Place of action",
        target_k=TARGET_COUNT_PER_LIST,
    )

    # -------- TWIST TYPES --------
    twist_items_all: List[str] = []
    for model in GENERATION_MODELS:
        vals = generate_list_with_model(
            client=client,
            model=model,
            system_prompt=TWIST_SYSTEM_PROMPT,
            list_name="twist types",
            n=SAMPLES_PER_MODEL_PER_LIST,
        )
        twist_items_all.extend(vals)
    random.shuffle(twist_items_all)
    twist_types = select_semantically_balanced(
        client=client,
        items=twist_items_all,
        prefix="Twist type",
        target_k=TARGET_COUNT_PER_LIST,
    )

    # -------- FINAL JSON --------
    result = {
        "genres": genres,
        "topics": topics,
        "settings": settings,
        "twist_types": twist_types,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved pools to {args.output}")


if __name__ == "__main__":
    main()
