"""Russian frequency dictionary, downloaded from the publisher on first use.

O. N. Lyashevskaya and S. A. Sharov. Frequency Dictionary of Modern Russian
(Based on the Russian National Corpus). Azbukovnik, Moscow, 2009. Electronic
edition: http://dict.ruslang.ru/freq.php

The publisher's lemma table carries no redistribution license, so the
repository keeps only this downloader. The table (20,004 lemmas by frequency)
is cached as CSV and checked against the version used to build the benchmark.
"""

import csv
import hashlib
import html
import io
import re
from pathlib import Path
from urllib.request import urlopen

# Plain HTTP: the site's HTTPS certificate does not cover dict.ruslang.ru.
URL = "http://dict.ruslang.ru/freq.php?act=show&dic=freq_freq"
SHA256 = "933ba579a1f4035563f16c84a63a71e446a2801968417a6f163ed7ceac83ed68"
HEADER = [
    "rank",
    "lemma",
    "lemma2",
    "pos",
    "freq_ipm",
    "fiction_1950s",
    "fiction_1970s",
    "fiction_1990s",
    "pub_1950s",
    "pub_1970s",
    "pub_1990s",
]
PATH = Path(__file__).parent / "resources" / "freq_dict_ruslang.csv"


def freq_dict_path(path: Path = PATH) -> Path:
    """Return the cached CSV, downloading and verifying it if absent."""
    if path.exists():
        return path
    print(f"Downloading the Russian frequency dictionary from {URL}")
    with urlopen(URL, timeout=300) as response:
        page = response.read().decode("cp1251")
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(HEADER)
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cells = [
            html.unescape(re.sub(r"<[^>]+>", "", cell)).replace("\xa0", " ").strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ]
        if cells and cells[0].isdigit():  # skip header and spacer rows
            writer.writerow(cells[: len(HEADER)])
    text = stream.getvalue()
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != SHA256:
        raise ValueError(
            f"{URL} no longer matches the dictionary used for the benchmark"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path
