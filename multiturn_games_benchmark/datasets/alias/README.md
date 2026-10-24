# Alias biography data

`Bio/` contains article text retrieved from English- and Russian-language
Wikipedia and serialized as Python pickle strings. MTGBench changes the storage
format and organizes the pages by task category and language; it does not claim
copyright in the underlying Wikipedia text.

Wikipedia text is available under [CC BY-SA 4.0][cc-by-sa] and, unless a page
states otherwise, the [GNU Free Documentation License][gfdl]. Reusers must
preserve attribution and share adaptations under the applicable terms. See
`ATTRIBUTION.tsv` for the title and source URL associated with each non-empty
payload.

The current artifacts do not contain the exact Wikipedia revision IDs or
retrieval timestamps. The titles in the manifest were recovered from the
title-preserving file paths in Git history by exact payload hash. Before public
release, either recover the original revision metadata or retrieve the pages
again while recording title, canonical URL, revision ID, retrieval timestamp,
license, and transformation notes.

The audit also found 23 empty payloads and six files under `Bio/**/ru/` whose
payload exactly matches an English Wikipedia source. The manifest flags these
rows. The six language mismatches are selected by `persons_ru`, so they should
be regenerated from Russian pages or explicitly documented as English fallback
context before reporting Alias as a fully Russian-language data condition.

[cc-by-sa]: https://creativecommons.org/licenses/by-sa/4.0/
[gfdl]: https://www.gnu.org/licenses/fdl-1.3.html
