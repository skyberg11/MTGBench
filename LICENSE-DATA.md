# Dataset license

Except for the third-party material listed below, original MTGBench datasets,
annotations, prompts, and metadata in this repository are licensed under the
[Creative Commons Attribution 4.0 International License][cc-by-4].

When reusing this material, cite the MTGBench paper and indicate whether you
modified the data. This grant does not override the terms of a model provider
for model-generated text contained in evaluation trajectories.

The CC BY 4.0 grant does **not** apply to these third-party or derived files:

- `multiturn_games_benchmark/datasets/word_chain/`: OpenStreetMap-derived locality data, ODbL 1.0;
- `multiturn_games_benchmark/datasets/alias/Bio/`: Wikipedia article text, CC BY-SA 4.0 and GFDL;
- `multiturn_games_benchmark/datasets/wordle/`: word lists derived from Princeton WordNet and RuWordNet;
- `multiturn_games_benchmark/datasets/wheel_of_fortune/en_letter_difficulty_words.json`: a list derived
  from the Brown Corpus and filtered with Princeton WordNet;
- `multiturn_games_benchmark/datasets/wheel_of_fortune/en_wordnet_nouns.csv`: a list of English noun lemmas
  from Princeton WordNet (used to compute baseline letter frequencies for the
  Wheel-of-Fortune analysis);
- `multiturn_games_benchmark/datasets/wheel_of_fortune/ru_letter_difficulty_words.json`: derived from the Russian
  frequency dictionary by O. N. Lyashevskaya and S. A. Sharov (the dictionary itself is
  downloaded from its publisher at run time and is not redistributed).

Those files retain their source terms. See [THIRD_PARTY_NOTICES.md] for the
source, attribution, and release status of each component.

[cc-by-4]: https://creativecommons.org/licenses/by/4.0/
[THIRD_PARTY_NOTICES.md]: THIRD_PARTY_NOTICES.md
