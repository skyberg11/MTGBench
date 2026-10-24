# Wordle normalization baselines

Each JSONL row contains `word` and `moves`, the historical algorithmic baseline turn count. The scoring pipeline uses `moves - 1` as the zero-based per-target floor. These are normalization inputs, not new game datasets. See the [baseline guide](../../../docs/repository.md#wordle-baseline).
