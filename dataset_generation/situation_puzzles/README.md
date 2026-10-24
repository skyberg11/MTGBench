# situation_puzzles: data preparation

`generate_lists.py` creates genre/topic/setting/twist pools and selects semantically diverse items. `generate_danetka.py` samples combinations, synthesizes puzzles, selects diverse candidates and runs quality evaluation. Use `--input` to choose settings and `--output` for candidates; `settings.json` is the bundled pool. All generation system templates are in `prompts/`. Final human checking and bilingual curation are required before using candidates as a benchmark. These English templates alone do not reproduce the released Russian set.

Paths are relative to the repository root unless local to this module. See the [command guide](../../docs/repository.md#auxiliary-commands) for runnable examples.

The original scripts contained a missing internal embedding endpoint. This release uses the configured OpenAI-compatible client’s embeddings API instead; set `--embedding-model` to an ID supported by that provider. This replacement is for generating new candidates and does not claim to recreate the original filtering exactly. Both generation and filtering templates, including parameterized user messages, are stored in `prompts/`.
