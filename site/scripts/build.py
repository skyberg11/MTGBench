"""Build the public static site using only Python's standard library."""
import csv
import json
import shutil
from pathlib import Path
from research_data import build_research

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / 'site'
OUT = ROOT / '.site-build'
OUT.mkdir(exist_ok=True)
for name in ('index.html', 'style.css', 'app.js', 'research.js', 'content.js', 'config.json'):
    shutil.copyfile(SITE / name, OUT / name)
shutil.copytree(SITE / 'assets', OUT / 'assets', dirs_exist_ok=True)
shutil.copytree(SITE / 'cards', OUT / 'cards', dirs_exist_ok=True)
source = ROOT / 'analysis/outputs/tables/summary.csv'
rows = list(csv.DictReader(source.open()))
keys = ('n', 'score', 'score_ci_low', 'score_ci_high', 'win_rate', 'win_rate_ci_low', 'win_rate_ci_high')
seen = set()
for row in rows:
    key = tuple(row[k] for k in ('model', 'mode', 'language', 'game'))
    assert key not in seen, f'Duplicate result: {key}'
    seen.add(key)
    for k in keys:
        row[k] = int(row[k]) if k == 'n' else float(row[k])
    for metric in ('score', 'win_rate'):
        assert 0 <= row[metric] <= 1
        assert 0 <= row[metric + '_ci_low'] <= row[metric + '_ci_high'] <= 1
(OUT / 'data.json').write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + '\n')
shutil.copyfile(source, OUT / 'summary.csv')
(OUT / '.nojekyll').touch()
(OUT / 'research.json').write_text(json.dumps(build_research(ROOT), ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
print(f'Built {len(rows)} validated result rows in {OUT}')
