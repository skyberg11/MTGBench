# twenty_questions: data preparation

`generate.py` constructs language-specific synthetic words, a hierarchical attribute pool and episode controllers. Run the module with `--language`, `--seed`, `--num-episodes` and required `--output`. This generator does not call an API. Its generated controller horizon and the runner’s fixed 20-question horizon are separate parameters.

Paths are relative to the repository root unless local to this module. See the [command guide](../../docs/repository.md#auxiliary-commands) for runnable examples.

New generation sorts attribute sets before random subsampling, making a fixed seed reproducible across Python processes. This repairs the original dependency on set iteration order. Released episode files are unchanged.
