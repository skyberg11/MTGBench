# [INTERACTIVE LEADERBOARD](https://skyberg11.github.io/MTGBench/)

# MTGBench

[Games](docs/games.md) · [Quickstart](#quickstart) · [Results and analysis](analysis/README.md) · [Repository guide](docs/repository.md)

<p align="center">
  <img src="docs/images/mtgbench_teaser.png" width="100%" alt="MTGBench: seven multi-turn games, an example Situation Puzzles dialogue between an LLM player and an LLM judge, and the benchmark protocol">
</p>

**Paper:** [*MTGBench: A Multi-Turn Game Benchmark for Diverse LLM Capability Assessment*](https://aclanthology.org/2026.findings-emnlp.1333/). Findings of EMNLP 2026.

MTGBench evaluates language models in seven multi-turn games in English and Russian. Four games use algorithmic evaluators, while three use constrained LLM verifiers. The benchmark compares answer-only, chain-of-thought, and native-reasoning configurations and provides datasets, model trajectories, and a Russian human baseline for reproducible analysis.


## Games

| Game | What the model does | Evaluator |
| --- | --- | --- |
| Word Chain | Name cities without breaking the chain or repeating a city | Algorithm |
| Wordle | Guess a five-letter noun from letter feedback | Algorithm |
| 20 Questions | Answer questions about a visible synthetic target consistently | Algorithm |
| Wheel of Fortune | Reveal letters and guess a hidden word | Algorithm |
| Situation Puzzles | Discover a hidden explanation through questions | LLM |
| 20 Features | Identify an object as features are revealed | LLM |
| Alias | Identify a public figure through questions about a biography | LLM |

[Game rules, examples and scoring](docs/games.md).

## Requirements

- Python 3.11 or newer
- An OpenAI-compatible API endpoint and API key
- NLTK WordNet data for English Wordle
- A RuWordNet database for Russian Wordle

The commands below assume a cloned repository. The Python wheel contains the
code, command-line entry point, default model configuration, and runtime prompt
templates, but it intentionally does not bundle the full benchmark datasets or
published result files.

## Installation

Clone the repository and enter its root directory:

```bash
git clone https://github.com/skyberg11/MTGBench.git
cd MTGBench
```

Install [`uv`](https://docs.astral.sh/uv/) and create an environment:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv --python 3.11
source .venv/bin/activate
```

Choose one installation command:

```bash
# Run the benchmark
uv pip install -e .

# Run the benchmark and analysis code
uv pip install -e ".[analysis]"

# Run dataset-generation code
uv pip install -e ".[dataset-generation]"
```

Install the external lexical resources required by Wordle:

```bash
# Required for English Wordle
python -m nltk.downloader wordnet

# Required for Russian Wordle
ruwordnet download
```

The Wheel of Fortune dataset-generation script additionally requires the NLTK
Brown Corpus:

```bash
python -m nltk.downloader brown
```

NLTK corpora and the RuWordNet database have their own terms of use. Review
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before downloading,
redistributing, or using these resources commercially.

## Configuration

`models.json` maps the short names used by `--model` and `--verifier` to
OpenAI-compatible model configurations. The repository includes example player
and verifier configurations for OpenRouter.

Set the API key and repository root before running the examples:

```bash
export api_key_env="your-token-here"
export INPUT_SCRIPT_PATH="$(pwd)"
```

The environment-variable name `api_key_env` is literal and case-sensitive.
`INPUT_SCRIPT_PATH` locates `models.json` and defaults to the current directory. Dataset paths are supplied independently with `--table-path`.

## Quickstart

After installation and configuration, run one English episode:

```bash
mtgbench wordle --model gpt-oss-120b --num-games 1 --max-attempts 20 \
  --table-path multiturn_games_benchmark/datasets/wordle/wordle_en.jsonl --seed 42 --language en
```

The command calls the configured model API. To inspect published results without API calls:

```bash
python -m analysis.reproduce --output-dir analysis/outputs
```

The analysis command produces one summary table with scores, win rates and 95% CI across all games, plus the paper’s two Wordle figures. It requires the `[analysis]` extra and a repository checkout. See [analysis outputs and reproducibility](analysis/README.md).

## Running the benchmark

Installing the project creates the `mtgbench` command. All examples below use
English datasets; replace the dataset suffix and pass `--language ru` for the
Russian condition.

### Word Chain

```bash
mtgbench word_chain \
    --model gpt-oss-120b \
    --num-games 100 \
    --max-attempts 25 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/word_chain/cities_en.jsonl" \
    --word_chain_path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/word_chain/cities_full_en.jsonl" \
    --word_chain_allowed "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/word_chain/cities_allowed_en.jsonl" \
    --seed 42 \
    --language en
```

### Wordle

```bash
mtgbench wordle \
    --model gpt-oss-120b \
    --num-games 100 \
    --max-attempts 20 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/wordle/wordle_en.jsonl" \
    --seed 42 \
    --language en
```

### Situation Puzzles

```bash
mtgbench situation_puzzles \
    --model gpt-oss-120b \
    --verifier deepseek-v4-flash_t=0 \
    --num-games 100 \
    --max-attempts 20 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/situation_puzzles/puzzles_final_en.jsonl" \
    --seed 42 \
    --language en
```

### 20 Questions

```bash
mtgbench twenty_questions \
    --model gpt-oss-120b \
    --num-games 100 \
    --max-attempts 20 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/twenty_questions_consistency/synthetic_en_400_episodes.jsonl" \
    --seed 42 \
    --language en
```

### Wheel of Fortune

```bash
mtgbench wheel_of_fortune \
    --model gpt-oss-120b \
    --num-games 100 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/wheel_of_fortune/en_letter_difficulty_words.json" \
    --seed 42 \
    --language en
```

### 20 Features

```bash
mtgbench twenty_features \
    --model gpt-oss-120b \
    --verifier deepseek-v4-flash_t=0 \
    --num-games 100 \
    --max-attempts 20 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/twenty_features" \
    --enable_nei false \
    --seed 42 \
    --language en
```

### Alias

```bash
mtgbench alias \
    --model gpt-oss-120b \
    --verifier deepseek-v4-flash_t=0 \
    --num-games 100 \
    --max-attempts 30 \
    --table-path "$INPUT_SCRIPT_PATH/multiturn_games_benchmark/datasets/alias" \
    --seed 42 \
    --language en
```

### CLI arguments

| Argument | Meaning | Default |
| --- | --- | --- |
| `game` | One of the seven game identifiers in the examples | Required |
| `--model` | Player configuration key in `models.json` | Required |
| `--table-path` | Dataset file; directory for Alias / 20 Features | Required |
| `--num-games` | Requested episodes before filtering game numbers | `10` |
| `--max-attempts` | Turn budget; exceptions below | `20` |
| `--seed` | Sampling and initial-state seed, not API determinism | Unset |
| `--language` | Prompts and dataset language (`ru`, `en`) | `ru` |
| `--CoT` | Add chain-of-thought instructions | Off |
| `--verifier` | Judge configuration for Situation Puzzles / Alias / 20 Features | Unset |
| `--game-numbers` | 1-based positions after sampling, e.g. `3,52,99` | All sampled episodes |
| `--word_chain_path` | Full city vocabulary, Word Chain only | Unset |
| `--word_chain_allowed` | Opponent city vocabulary, Word Chain only | Unset |
| `--enable_nei` | 20 Features only: permit requesting another feature with `nei` (`true`, `false`); ignored by other games | `false` |
| `-h`, `--help` | Show help without running a model | — |

20 Questions always uses 20 attempts. Wheel of Fortune uses 26 attempts in English and 29 in Russian and requests `num_games // 5` episodes from each of five stored sampling strata; use a positive multiple of five and stay within the available samples per stratum. These two games do not use `--max-attempts`.

Situation Puzzles, Alias and 20 Features require `--verifier`. Word Chain needs both city-vocabulary paths. Examples illustrate usage; inference settings for the paper also depend on the player configuration in `models.json`.

### Reasoning modes

AO is the default for all seven games. Add `--CoT` to any command to enable the
CoT prompt for Word Chain, Wordle, Situation Puzzles, 20 Questions, Wheel of
Fortune, 20 Features, or Alias.

`--enable_nei` applies only to 20 Features (`twenty_features`) and has no effect
on other games. Setting `--enable_nei true` allows the model to request another
feature by answering `nei`. The reported benchmark configuration uses
`--enable_nei false`.

## Outputs

By default, each run writes a timestamped JSON file under `results/`. Set
`JSON_OUTPUT_FILE` to write to a specific path:

```bash
export JSON_OUTPUT_FILE="/tmp/mtgbench-results.json"
```

The output contains aggregate statistics, per-game trajectories, prompts,
targets, token counts, and raw model responses.

## Data, limitations, and responsible use

Data combines lexical and geographic resources, synthetic tasks, LLM-assisted generation and human validation. Source vocabularies may contain sensitive terms; LLM generators and verifiers can introduce bias or errors. Six Russian Alias episodes use English-source biography context. Human results describe a small Russian-speaking sample.

See [data and ethics](docs/data_and_ethics.md) for sources and limitations, and [repository guide](docs/repository.md) for dataset preparation.

## Licenses and attribution

Benchmark code is released under the [MIT License](LICENSE). Original MTGBench
datasets, annotations, prompts, and metadata are released under
[CC BY 4.0](LICENSE-DATA.md).

Third-party and derived resources are excluded from the CC BY grant and retain
their original terms. In particular:

- Word Chain locality data is derived from OpenStreetMap and remains under
  ODbL.
- Alias biographies are Wikipedia content under CC BY-SA/GFDL.
- Wordle and Wheel of Fortune lexical resources have source-specific terms.

Read [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing the
datasets or publishing a derived artifact.

## Repository layout

```text
dataset_generation/         Preparation code and resources, grouped by game
multiturn_games_benchmark/    Game environments, prompts, baselines and datasets
  games/                     Environments and evaluators
  prompts/                   Player and verifier templates, EN/RU
  baselines/                 Algorithmic Wordle player
  datasets/                  Released game inputs and attribution
results/                     Released LLM, human and baseline results
analysis/                    Scores, tables and figures from local results
site/                        Interactive website, assets and build scripts
docs/                        Game rules, repository guide and data statement
```

See [repository guide](docs/repository.md) for commands, inputs and outputs of auxiliary tools.
