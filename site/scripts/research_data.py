"""Build aggregate chart data without shipping episode transcripts.

Wordle reproduces analysis.plots.wordle.diagnostic_score and mean_ci using
stdlib only. The other chart inputs are the released analysis CSV tables.
"""
import csv
import json
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict

SELECTED_MODELS = (
    'gemini-3.1-pro-preview', 'gpt-5.4', 'deepseek-v4-pro',
    'qwen3-235b-a22b-thinking-2507', 'qwen3.5-35b-a3b', 'gpt-5.4-mini',
)


def read_csv(path, numbers, integers=()):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for field in numbers:
            row[field] = float(row[field])
        for field in integers:
            row[field] = int(row[field])
    return rows


def wordle_difficulty(root, models):
    dataset = [json.loads(line) for line in (root / 'multiturn_games_benchmark/datasets/wordle/wordle_ru.jsonl').read_text().splitlines() if line.strip()]
    buckets = {row['word']: int(row['bucket']) for row in dataset}
    baselines = {row['word'].lower().replace('ё', 'е'): row['moves'] for row in (json.loads(line) for line in (root / 'results/baselines/wordle/ru_baseline.jsonl').read_text().splitlines() if line.strip())}
    grouped = defaultdict(list)
    for model in models:
        for path in sorted((root / 'results/wordle' / model).glob('ru_*.json')):
            result = json.loads(path.read_text())
            for episode in result['episodes']:
                if episode['status'] not in {'won', 'lost'}:
                    continue
                target = episode.get('target') or dataset[int(episode['id'].removeprefix('wordle_')) - 1]['word']
                baseline = baselines[target.lower().replace('ё', 'е')]
                assert 0 <= baseline < 20
                score = max(0, min(1, 1 - (episode['turns'] - baseline) / (20 - baseline))) if episode['won'] else 0
                grouped[(model, result['mode'], buckets[target])].append(score)
    rows = []
    for (model, mode, bucket), values in sorted(grouped.items()):
        mean = statistics.mean(values)
        error = 1.96 * statistics.stdev(values) / len(values) ** .5 if len(values) > 1 else 0
        rows.append(dict(model=model, mode=mode, bucket=('Easy', 'Medium', 'Hard')[bucket - 1], n=len(values), score=mean, score_ci_low=mean-error, score_ci_high=mean+error))
    return rows


def judge_agreement(root):
    """Read the 24 published values directly from the poster's vector table.

    Per-judgment records are not in the release; do not imply recalculation.
    Fail on a changed table layout rather than silently publishing stale values.
    """
    poster = ET.parse(root / 'site/assets/poster.svg').getroot()
    figure = next(node for node in poster.iter() if node.get('id') == 'fig_judge_agreement')
    cells = []
    for node in figure.iter():
        if (node.tag.split('}')[-1] != 'text'
                or float(node.get('x', 0)) < 200
                or float(node.get('y', 0)) < 50):
            continue
        value = ''.join(node.itertext()).strip()
        if value == '—':
            cells.append(None)
        else:
            try:
                cells.append(float(value))
            except ValueError:
                pass
    assert len(cells) == 24, 'Poster judge-agreement table layout changed'
    assert all(value is None or 0 <= value <= 1 for value in cells)
    conditions = [('alias', 'ru', ''), ('alias', 'en', ''), ('twenty_features', 'ru', ''), ('twenty_features', 'en', ''), ('situation_puzzles', 'ru', 'strict'), ('situation_puzzles', 'ru', 'soft'), ('situation_puzzles', 'en', 'strict'), ('situation_puzzles', 'en', 'soft')]
    return [dict(game=g, language=lang, criterion=criterion, gpt=cells[i*3], gemini=cells[i*3+1], human=cells[i*3+2]) for i, (g, lang, criterion) in enumerate(conditions)]


def build_research(root):
    tables = root / 'analysis/outputs/tables'
    with (tables / 'summary.csv').open() as stream:
        summary = list(csv.DictReader(stream))
    models = sorted({row['model'] for row in summary if row['model'] != 'human'})
    wordle = wordle_difficulty(root, models)
    wheel = read_csv(tables / 'wheel_of_fortune_per_level_speed_trend_3bin_ru.csv', ('score', 'score_ci_low', 'score_ci_high'), ('n',))
    for game, rows in [('wordle', wordle), ('wheel_of_fortune', wheel)]:
        expected = {(row['model'], row['mode'], bucket) for row in summary
                    if row['game'] == game and row['language'] == 'ru' and row['model'] != 'human'
                    for bucket in ('Easy', 'Medium', 'Hard')}
        keys = {(row['model'], row['mode'], row['bucket']) for row in rows}
        assert keys == expected and len(keys) == len(rows), f'Incomplete or duplicate {game} difficulty data'
        assert all(row['n'] > 0 and 0 <= row['score'] <= 1
                   and row['score_ci_low'] <= row['score_ci_high'] for row in rows)
    correlations = read_csv(tables / 'cognitive_correlation_kendall.csv', ('tau_b', 'p_value'), ('n',))
    for row in correlations:
        row['significant'] = row['significant'] == 'True'
        assert -1 <= row['tau_b'] <= 1 and 0 <= row['p_value'] <= 1
    return {
        'selectedModels': SELECTED_MODELS,
        'wordleDifficulty': wordle,
        'wheelDifficulty': wheel,
        'correlations': correlations,
        'judgeAgreement': judge_agreement(root),
        'sources': {
            'wordleDifficulty': 'analysis/plots/wordle.py',
            'wheelDifficulty': 'analysis/outputs/tables/wheel_of_fortune_per_level_speed_trend_3bin_ru.csv',
            'correlations': 'analysis/outputs/tables/cognitive_correlation_kendall.csv',
            'judgeAgreement': 'site/assets/poster.svg',
        },
    }
