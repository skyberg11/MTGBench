"""English noun corpus for the Wheel of Fortune conditional-letter analysis.

Single-word, alphabetic Princeton WordNet 3.0 noun lemmas of 3-14 letters, in
the column layout of the Russian frequency dictionary. WordNet has no
frequencies, so `freq_ipm` is 0 and `rank` is alphabetical.
"""

import argparse
import csv

import nltk
from nltk.corpus import wordnet


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", required=True, help="Path to output CSV")
    args = parser.parse_args()

    nltk.download("wordnet", quiet=True)
    words = sorted(
        lemma
        for lemma in wordnet.all_lemma_names(pos=wordnet.NOUN)
        if lemma.isalpha() and 3 <= len(lemma) <= 14
    )
    with open(args.output, "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["rank", "lemma", "lemma2", "pos", "freq_ipm"])
        writer.writerows(
            [rank, word, word, "s", 0] for rank, word in enumerate(words, 1)
        )
    print(f"Wrote {len(words)} nouns to {args.output}")


if __name__ == "__main__":
    main()
