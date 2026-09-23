'''고정 시드로 기사·판정 예시를 만들고 엑셀 작성용 JSON을 내보낸다.'''

import argparse
import json
from pathlib import Path
from random import Random

import pandas as pd

SEED = 20260923


def build_examples(directory, start='2016-01-01', end='2025-12-31', seed=SEED):
  directory = Path(directory)
  conflicts = pd.read_excel(directory / 'conflicts.xlsx')
  categories = pd.read_excel(directory / 'categories.xlsm').set_index('category_id')
  weapons = pd.read_excel(directory / 'SIPRI_dictionary.xlsx')
  technologies = pd.read_excel(directory / 'NATO_dictionary.xlsx')
  names = (
    pd.concat(
      [
        weapons[['category_id', 'wp_name']].rename(columns={'wp_name': 'name'}),
        technologies[['category_id', 'tech_name']].rename(
          columns={'tech_name': 'name'}
        ),
      ]
    )
    .groupby('category_id')['name']
    .agg(list)
  )
  weapon_ids = sorted(weapons['category_id'].unique())
  technology_ids = sorted(technologies['category_id'].unique())
  random = Random(seed)
  articles, results = [], []
  for month in pd.period_range(start, end, freq='M'):
    first = max(month.start_time.normalize(), pd.Timestamp(start))
    last = min(month.end_time.normalize(), pd.Timestamp(end))
    days = (last - first).days
    for conflict in conflicts.itertuples(index=False):
      count = random.randint(12, 24)
      dates = [first, last] + [
        first + pd.Timedelta(days=random.randint(0, days)) for _ in range(count - 2)
      ]
      for published_date in sorted(dates):
        article_id = len(articles) + 1
        mode = article_id % 6
        selected = []
        if mode in (0, 2, 4, 5):
          selected.extend(random.sample(weapon_ids, 2 if mode in (2, 5) else 1))
        if mode in (1, 3, 4, 5):
          selected.extend(random.sample(technology_ids, 2 if mode == 3 else 1))
        if article_id % 17 == 0:
          selected = []
        topic = '·'.join(categories.loc[selected, 'category_name']) or '분쟁 일반 동향'
        articles.append(
          [
            article_id,
            conflict.conflict_id,
            published_date.strftime('%Y-%m-%d'),
            f'https://example.invalid/articles/{article_id:06d}',
            f'[가상 기사] {conflict.conflict_name_ko} {topic} 보도 {article_id}',
          ]
        )
        for category_id in selected:
          usage_code = random.choices([0, 1, 2], weights=[4, 5, 1])[0]
          term = random.choice(names[category_id])
          if usage_code == 1:
            evidence = f'[Synthetic] Fictional units used {term} in this example.'
          elif usage_code == 0:
            evidence = (
              f'[Synthetic] Procurement of {term} was discussed; no use was reported.'
            )
          else:
            evidence = f'[Synthetic] Possible use of {term} could not be verified.'
          results.append([article_id, category_id, usage_code, evidence])
  return {
    'articles': {
      'columns': [
        'article_id',
        'conflict_id',
        'published_date',
        'article_url',
        'title',
      ],
      'rows': articles,
    },
    'result': {
      'columns': ['article_id', 'category_id', 'usage_code', 'evidence_sentence'],
      'rows': results,
    },
  }


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    '--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'data/dummy'
  )
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  examples = build_examples(args.directory)
  args.output.write_text(json.dumps(examples, ensure_ascii=False), encoding='utf-8')
  print({name: len(data['rows']) for name, data in examples.items()})


if __name__ == '__main__':
  main()
