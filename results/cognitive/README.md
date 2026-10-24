# Cognitive benchmark data

Committed inputs for the cognitive analysis — the Figure 3 correlation (cognitive
skills × game performance) and the appendix cognitive-scores table. See
[`analysis/README.md`](../../analysis/README.md) for how they are used.

## `trajectories/` — the released cognitive trajectories

- **`trajectories/single_turn/<model>.json`** — one file per model. Each item is
  a benchmark question's `id`, the model's `response`, the `extracted_answer`, the
  `gold` answer, and whether it was `correct`. Aggregating these reproduces the 9
  single-turn benchmark scores exactly (`num_correct / N`; emotional intelligence
  uses `mean(score) / 100`).
- **`trajectories/inputs/<benchmark>.jsonl`** — the benchmark **questions**, keyed
  by `id`. Stored once (identical across models) rather than duplicated per model.

## `multiturn_scores.csv` — multi-turn scores (not recomputable here)

We share only computed scores for the two multi-turn benchmarks (working memory / N-back, cognitive flexibility / WCST + LNT), as trajectories were not stored as part of running those two benchmarks.
