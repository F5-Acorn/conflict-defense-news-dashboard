'''화면 디자인 상수와 현재 데이터에서 계산하는 조회 설정.'''

from data.constants import KIND_LABELS

CATEGORY_PALETTE = (
  '#3296ff',
  '#20d6cf',
  '#ffd052',
  '#ab8dff',
  '#ff8ab4',
  '#7fd28c',
  '#efab68',
)
CHART_BACKGROUND = '#0b1b26'
GRID_COLOR = '#243d50'
TEXT_COLOR = '#b8d0e8'


def build_settings(tables):
  '''현재 입력 스냅샷에서 범주·분쟁·기간과 화면 색상을 계산한다.'''
  category_ids = {
    label: tables['categories']
    .loc[tables['categories']['kind'].eq(code)]
    .set_index('category_name')['category_id']
    .to_dict()
    for code, label in KIND_LABELS.items()
  }
  categories = {label: sorted(names) for label, names in category_ids.items()}
  conflicts = {
    row.conflict_name_ko: {
      'color': row.color,
      'location': (row.latitude, row.longitude),
      'flag': row.flag,
    }
    for row in tables['conflicts'].fillna({'flag': ''}).itertuples(index=False)
  }
  dates = tables['articles']['published_date']
  return {
    'categories': categories,
    'conflict_names_by_id': dict(
      zip(tables['conflicts']['conflict_id'], tables['conflicts']['conflict_name_ko'])
    ),
    'category_ids': category_ids,
    'classification_counts': {kind: len(names) for kind, names in categories.items()},
    'conflicts': conflicts,
    'start': dates.min().date() if not dates.empty else None,
    'end': dates.max().date() if not dates.empty else None,
    'category_colors': {
      kind: {
        name: CATEGORY_PALETTE[index % len(CATEGORY_PALETTE)]
        for index, name in enumerate(names)
      }
      for kind, names in categories.items()
    },
  }
