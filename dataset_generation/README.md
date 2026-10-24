# Dataset generation

Preparation code, templates and source resources are grouped by game in this top-level package. Released gameplay inputs live under `multiturn_games_benchmark/datasets/`.

- [twenty_features](twenty_features/README.md)
- [twenty_questions](twenty_questions/README.md)
- [wheel_of_fortune](wheel_of_fortune/README.md)
- [situation_puzzles](situation_puzzles/README.md)

Generators exist for 20 Questions, Wheel of Fortune and Situation Puzzles. The 20 Features directory contains generation prompts; its full generation pipeline is not included. No command in the analysis pipeline regenerates game data or calls an LLM.
