# Benchmark results

LLM trajectories are stored as one aggregate file per game, model, language,
and inference mode:

```text
results/<game>/<model>/<language>_<mode>.json
```

The supported languages are `en` and `ru`. The modes are `answer_only`, `cot`,
and `reasoning`. Not every model supports every mode.

Each file follows schema version `1.0`:

```json
{
  "schema_version": "1.0",
  "game": "wordle",
  "model": "gpt-4.1",
  "language": "en",
  "mode": "answer_only",
  "episodes": [
    {
      "id": "wordle_1",
      "status": "won",
      "won": true,
      "turns": 3,
      "target": "story",
      "initial_prompt": "...",
      "dialogue": [
        {
          "turn": 1,
          "model_response": "Answer: ...",
          "parsed_action": "...",
          "feedback": "...",
          "is_valid": true
        }
      ]
    }
  ]
}
```

Episode fields are omitted when they were not recorded in the original run.
Provider debug payloads, endpoints, credentials, timing data, and internal
metadata are intentionally excluded. Interrupted episodes are retained so the
published trajectories remain complete.

The LLM results were consolidated from the original `json_files`,
`llm_benchmark`, and `results_*` exports. Six exploratory runs that are not part
of the paper's model matrix were excluded. The existing raw human sessions remain
available separately under [`human_benchmark`](human_benchmark/).

## Analysis

Run `python -m analysis.reproduce` from the repository root to compute the summary table with scores, win rates and 95% CI, and reproduce the Wordle figures. See [analysis documentation](../analysis/README.md) for scoring, human aggregation and Wordle calculations. Historical Wordle baseline counts live in [baselines/wordle](baselines/wordle/).
