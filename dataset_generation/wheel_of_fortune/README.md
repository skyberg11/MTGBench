# wheel_of_fortune: data preparation

`generate.py` derives a mean letter-rarity score for words and emits five sampling strata A2–C2. Russian input defaults to the Lyashevskaya–Sharov frequency dictionary, which [`freq_dict.py`](freq_dict.py) downloads from its publisher on first use into `resources/freq_dict_ruslang.csv` (not redistributed; see [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md#russian-lexical-resources)); English defaults to the NLTK Brown vocabulary with optional WordNet noun filtering. `--output` is required.

Paths are relative to the repository root unless local to this module. See the [command guide](../../docs/repository.md#auxiliary-commands) for runnable examples.
