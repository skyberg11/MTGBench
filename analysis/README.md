# Results and paper figures

Run from a repository checkout:

```bash
uv pip install -e ".[analysis]"
python -m analysis.reproduce --output-dir analysis/outputs
```

This produces score and win-rate tables with 95% confidence intervals, the cognitive-benchmark tables and the paper's analysis figures. Use `--no-plots` for tables only; `--resamples 10000 --seed 42` sets the bootstrap parameters. The default output files are tracked in Git and overwritten on rerun.

## Scores and data

AO, CoT and native reasoning are reported separately. `Total` equally weights the seven game means. See [game scores](../docs/games.md#score-and-win-rate) and [scoring.py](scoring.py) for formulas. Confidence intervals use percentile bootstrap within each game; human intervals resample aggregated targets. The paper’s original bootstrap seed is unavailable.

The analysis uses 39,157 LLM episodes and 476 human sessions, aggregated into 453 game/target observations by majority outcome (ties count as wins) and rounded mean turns.