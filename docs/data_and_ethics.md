# Data, limitations, and responsible use

## Data statement

MTGBench contains English and Russian game conditions. The benchmark combines
automatically collected lexical resources, geographic data, procedurally
generated data, LLM-assisted generation, and human validation.

Wordle and Wheel of Fortune use noun vocabularies in the corresponding
language. English lexical validation uses NLTK WordNet; Russian lexical
validation uses RuWordNet. These resources may contain terms referring to
social groups or sensitive, offensive, taboo, or otherwise harmful topics.
Their presence reflects source-resource coverage and does not represent the
authors' views or endorsement.

Word Chain uses a static database of real-world city and town names derived
from the Geoapify/OpenStreetMap locality export. Names are normalized for
validation and opponent-move generation. The data may include politically or
culturally sensitive place names.

20 Questions uses procedurally generated, morphologically
plausible non-existent words and synthetic hierarchical attributes. It is
designed not to rely on factual world knowledge.

Situation Puzzles, 20 Features, and Alias use combinations of LLM-based
generation, automatic filtering, and human validation or external retrieval.
Alias uses public-figure biographies retrieved from Wikipedia. The selected
English and Russian lists contain no empty biography payloads. However, six
biographies selected for the current Russian Alias condition contain English
Wikipedia text as fallback context; see
[multiturn_games_benchmark/datasets/alias/README.md](../multiturn_games_benchmark/datasets/alias/README.md) and
[multiturn_games_benchmark/datasets/alias/ATTRIBUTION.tsv](../multiturn_games_benchmark/datasets/alias/ATTRIBUTION.tsv).

Alias uses biographies of notable public figures and is not intended to make normative judgments about them. Human game sessions are described separately below.

## Ethics statement

The benchmark evaluates multi-turn reasoning, consistency,
information-seeking, and planning in controlled games. Several limitations
remain:

- Broad lexical and geographic resources can contain sensitive or socially
  charged items.
- LLM-generated datasets may reproduce biases, stereotypes, cultural
  assumptions, or generator-specific artifacts.
- Cross-language scores should not be interpreted as measures of the intrinsic
  quality or cultural value of either language.

Users should inspect the datasets for their intended application, apply
additional filtering when needed, and report these limitations alongside
benchmark results.

## Human baseline

The release contains 476 retained sessions from paid, voluntary native Russian-speaking participants recruited within the authors' affiliated organization. The paper reports 483 collected sessions and seven early test-session exclusions; those seven are already absent from the released result files. No demographic information was collected. Participants could choose games and were not prohibited from using external tools, so this is a small, non-representative comparison group.

The released files use participant labels such as `player1` and include gameplay, timestamps and durations. Multiple sessions for the same target are aggregated using majority outcome (ties count as a win) and rounded mean turns before scoring. The analysis ignores `._*` macOS resource-fork files. See [analysis](../analysis/README.md) for the exact procedure.

## Licenses

See [code license](../LICENSE), [data license](../LICENSE-DATA.md), [third-party notices](../THIRD_PARTY_NOTICES.md), and per-dataset attributions. Prompts retain their existing data-license scope when moved into the Python package.
