# Third-party notices and release audit

This file records the provenance and licensing scope of data distributed with
MTGBench. A dependency's software license does not automatically license the
linguistic or geographic database used through that dependency.

## Word Chain: Geoapify and OpenStreetMap

Files: `multiturn_games_benchmark/datasets/word_chain/*.jsonl`.

The locality database was downloaded from Geoapify's world cities export,
which is compiled from OpenStreetMap and offered under the Open Database
License 1.0 (ODbL). MTGBench normalizes names, separates languages, retains
alternative names where available, and filters the source into gameplay and
validation files.

Required attribution:

> Contains information from OpenStreetMap, which is made available here under
> the Open Database License (ODbL). © OpenStreetMap contributors.

- Source: https://www.geoapify.com/download-all-the-cities-towns-villages/
- License: https://opendatacommons.org/licenses/odbl/1-0/
- Contributors: https://www.openstreetmap.org/copyright
- Detailed notice: `multiturn_games_benchmark/datasets/word_chain/README.md`

These database files remain under ODbL; they are not covered by the repository's
CC BY 4.0 data license. Redistribution is permitted with attribution and the
ODbL share-alike requirements for an adapted database.

## Alias: Wikipedia biographies

Files: `multiturn_games_benchmark/datasets/alias/Bio/**`.

The biography payloads were retrieved from English- and Russian-language
Wikipedia using `wikipediaapi`. Wikipedia text is available under CC BY-SA 4.0
and, unless a page says otherwise, the GNU Free Documentation License. MTGBench
stores extracted article text in Python pickle files and changes its format.

- Source project: https://www.wikipedia.org/
- CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/
- GFDL: https://www.gnu.org/licenses/fdl-1.3.html
- Wikimedia reuse guidance: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- Per-file attribution: `multiturn_games_benchmark/datasets/alias/ATTRIBUTION.tsv`
- Detailed notice: `multiturn_games_benchmark/datasets/alias/README.md`

The source titles in `ATTRIBUTION.tsv` were recovered by matching the current
payloads to the earlier, title-preserving files in this repository's Git
history. The original retrieval process did not record page revision IDs or
retrieval timestamps. Exact revision attribution must therefore be recovered
or the biographies must be fetched again with title, URL, revision ID, and
timestamp metadata before a public release.

The attribution audit flags 23 empty payloads and six Russian-directory files
that contain English-source text. All six language mismatches occur in the
current `persons_ru` selection. This is both a provenance and benchmark-quality
issue and should be resolved or explicitly documented before release.

## English lexical resources

Princeton WordNet is distributed under the permissive WordNet 3.0 license. It
is used to validate English Wordle guesses and to filter nouns. The file
`multiturn_games_benchmark/datasets/wheel_of_fortune/en_wordnet_nouns.csv` is a list of single-word English
noun lemmas extracted from Princeton WordNet by
`dataset_generation/wheel_of_fortune/wordnet_nouns.py` (the `freq_ipm` column is a
placeholder and carries no frequency data); it is covered by the same permissive
WordNet 3.0 license.

- WordNet license: https://wordnet.princeton.edu/license-and-commercial-use

NLTK 3.9.3 source code is Apache-2.0, but the NLTK data packages have their own
terms. In particular, NLTK's dataset license registry marks the Brown Corpus as
non-commercial/educational use. The file
`multiturn_games_benchmark/datasets/wheel_of_fortune/en_letter_difficulty_words.json` was generated from
Brown Corpus frequencies and must not be presented as CC BY 4.0.

- NLTK software license: https://github.com/nltk/nltk/blob/develop/LICENSE.txt
- NLTK dataset registry: https://github.com/nltk/nltk_data/blob/gh-pages/DATASET-LICENSES.md

**Release status:** replace the Brown-derived list with a source whose license
permits the intended redistribution, or obtain and document permission before
claiming that the complete benchmark data is openly redistributable.

## Russian lexical resources

The `ruwordnet` 0.0.6 Python wrapper is Apache-2.0. That software license does
not by itself license the RuWordNet thesaurus database used for validation.
The repository does not bundle the RuWordNet database, but users must obtain it
under the provider's terms. The official RuWordNet site states that the
thesaurus is distributed for non-commercial use and instructs users to contact
the resource maintainers to obtain its XML files.

`multiturn_games_benchmark/datasets/wordle/wordle_ru.jsonl` is a target list derived using that thesaurus
and is therefore excluded from the repository's CC BY 4.0 grant. Treat it as a
RuWordNet-derived resource unless the resource maintainer confirms broader
redistribution terms.

- Wrapper: https://github.com/avidale/python-ruwordnet
- Thesaurus and terms: https://ruwordnet.ru/en/
- Resource publication: https://dialogue-conf.org/media/3478/dialogue2016.pdf

The Russian Wheel of Fortune source list is the lemma frequency table of the
electronic edition of:

> O. N. Lyashevskaya and S. A. Sharov. *Frequency Dictionary of Modern Russian
> (Based on the Russian National Corpus).* Azbukovnik, Moscow, 2009.

- Electronic edition: http://dict.ruslang.ru/freq.php
- Table used: http://dict.ruslang.ru/freq.php?act=show&dic=freq_freq
  (20,004 lemmas by frequency)

**Release status:** the derived
`multiturn_games_benchmark/datasets/wheel_of_fortune/ru_letter_difficulty_words.json`
(1,250 selected nouns with letter-rarity scores) is not sublicensed under
CC BY 4.0; it retains the source's terms.
