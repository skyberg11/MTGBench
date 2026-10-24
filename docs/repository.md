# Repository guide

| Path | Purpose |
| --- | --- |
| `main.py` | `mtgbench` CLI, dataset selection and game construction |
| `models.json` | OpenAI-compatible player and verifier configurations |
| `multiturn_games_benchmark/games/` | Game rules and evaluators |
| `multiturn_games_benchmark/prompts/` | Runtime player and verifier templates; packaged with the code |
| `dataset_generation/` | Generation, filtering prompts, settings and source resources by game |
| `multiturn_games_benchmark/baselines/` | Algorithmic comparison players |
| `multiturn_games_benchmark/datasets/` | Released inputs, schema notes and source attribution |
| `results/` | Published trajectories, human sessions and Wordle baseline turn counts |
| `analysis/` | Summary scores, win rates, confidence intervals and Wordle figures |
| `docs/` | Game explanations, repository guide and data statement |

`dataset_generation` is a top-level Python package so tools run with `python -m dataset_generation.<game>.<module>`. Released datasets live under `multiturn_games_benchmark/datasets/` and are passed explicitly to games. `multiturn_games_benchmark/datasets/twenty_questions_consistency/` is the dataset for the `twenty_questions` CLI game. Historical result names `cities`, `danetka` and `field_of_miracles` correspond to Word Chain, Situation Puzzles and Wheel of Fortune.

## Auxiliary commands

Run commands from the repository root. Each generator writes to the explicitly supplied output path; use a scratch directory when making new data.

| Task | Command | Inputs / output | Extra / API |
| --- | --- | --- | --- |
| Analyze results | `python -m analysis.reproduce --output-dir analysis/outputs` | Published results → summary table (CSV/Markdown/LaTeX) and Wordle figures (PNG/PDF) | `[analysis]`; no API |
| Wordle baseline | `python -m multiturn_games_benchmark.baselines.wordle --dataset multiturn_games_benchmark/datasets/wordle/wordle_en.jsonl --num-games 1 --seed 42 --max-attempts 20 --output /tmp/wordle-baseline.json` | Five-letter vocabulary → trajectory JSON | Base install; no API |
| 20 Questions data | `python -m dataset_generation.twenty_questions.generate --num-episodes 2 --language en --seed 42 --output /tmp/20q.jsonl` | Synthetic hierarchy → episode JSONL | `[dataset-generation]`; no API |
| Wheel of Fortune data | `python -m dataset_generation.wheel_of_fortune.generate --language ru --nouns-only --words-per-level 2 --output /tmp/wof.json` | Frequency dictionary (downloaded on first use) → word difficulty JSON | `[dataset-generation]`; no API; English default also needs Brown / WordNet |
| Situation Puzzle pools | `python -m dataset_generation.situation_puzzles.generate_lists --output /tmp/settings.json` | LLM-generated pools → diversified settings JSON | `[dataset-generation]`; model and embedding API |
| Situation Puzzle candidates | `python -m dataset_generation.situation_puzzles.generate_danetka --input /tmp/settings.json --output /tmp/puzzles.json` | Settings → generated, filtered candidates | `[dataset-generation]`; model and embedding API; manual validation follows |

Every command supports `--help`. The situation-puzzle tools accept `api_key_env` and legacy `TOKEN`; model IDs, endpoint and seed can be supplied on the command line. Their current templates are English. A seed controls local sampling, not remote model determinism.

## Preparing new datasets

See the [generation guide](../dataset_generation/README.md). A generated candidate file is not automatically the published benchmark: diversity filtering and manual validation are part of preparation. Ready-to-play resources and their schema are documented under [datasets](../multiturn_games_benchmark/datasets/README.md).

## Wordle baseline

The entropy player has access to the supplied candidate vocabulary, whereas the evaluated LLM does not receive a candidate list. It reproduces the benchmark’s independent repeated-letter feedback rule. The checked-in `results/baselines/wordle/*_baseline.jsonl` files contain historical per-target turn counts used for scoring. A fresh run with a different vocabulary does not replace those normalization inputs.

## Build

```bash
uv pip install build
python -m build
```

The wheel includes benchmark code, runtime prompts, and the `dataset_generation` package with its templates and source resources. Full datasets and published results require a checkout and are excluded from both the wheel and source distribution. The source distribution also includes analysis and documentation.

CI installs the `[analysis]` and `[dataset-generation]` extras, checks the CLI and generation templates, runs a one-game Wordle baseline and small 20 Questions and Russian Wheel of Fortune generators, regenerates the English Wheel of Fortune analysis corpus and checks it against the committed file, reproduces the analysis with 100 bootstrap resamples, and builds both distributions. These checks download the Russian frequency dictionary from its publisher and do not call a model API. Temporary outputs are written outside the checkout; the published datasets and results are not overwritten.
