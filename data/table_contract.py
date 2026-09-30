'''화면용 여섯 테이블의 내부 자료형·키·관계를 검증한다.'''

import re

import pandas as pd

from data.constants import KIND_LABELS, UsageCode

COLUMNS = {
  'conflicts': [
    'conflict_id',
    'conflict_name_en',
    'conflict_name_ko',
    'color',
    'flag',
    'latitude',
    'longitude',
  ],
  'categories': ['category_id', 'kind', 'category_name'],
  'sipri_dictionary': ['wp_id', 'category_id', 'wp_name'],
  'nato_dictionary': ['tech_id', 'category_id', 'tech_name'],
  'articles': ['article_id', 'conflict_id', 'published_date', 'article_url', 'title'],
  'result': ['article_id', 'category_id', 'usage_code', 'evidence_sentence'],
}


class DataValidationError(ValueError):
  '''연결 설정 또는 화면 입력 데이터 오류.'''


def _invalid(name, message):
  raise DataValidationError(f'[{name} 테이블] {message}')


def _unique(name, frame, columns):
  if frame.duplicated(columns).any():
    _invalid(name, f'{", ".join(columns)} 값이 중복되었습니다.')


def _integers(name, column, values, minimum, maximum):
  '''큰 ID가 잘못된 값과 섞여 있어도 float로 변환해 정밀도를 잃지 않는다.'''
  converted = []
  for value in values:
    text = str(value).strip()
    if not re.fullmatch(r'[0-9]+', text):
      _invalid(name, f'{column} 값이 올바른 정수가 아닙니다.')
    number = int(text)
    if not minimum <= number <= maximum:
      _invalid(name, f'{column} 값이 올바른 정수 범위가 아닙니다.')
    converted.append(number)
  return pd.Series(converted, index=values.index, dtype='int64')


def _validate_columns(name, frame, columns):
  '''한 테이블의 필수값·자료형·정수 범위·기본키를 검증한다.'''
  missing = set(columns) - set(frame.columns)
  if missing:
    _invalid(name, f'필수 컬럼이 없습니다: {", ".join(sorted(missing))}')
  nullable = {'flag', 'evidence_sentence', 'title'}
  for column in columns:
    if column not in nullable:
      blank = frame[column].isna() | frame[column].astype(str).str.strip().eq('')
      if blank.any():
        _invalid(
          name, f'{column}에 빈값이 있습니다 (데이터 {blank.idxmax() + 1}번째 행).'
        )
    if column not in {
      'article_id',
      'usage_code',
      'published_date',
      'latitude',
      'longitude',
    }:
      present = frame[column].dropna()
      if not all(isinstance(value, str) for value in present):
        _invalid(name, f'{column}은 문자열이어야 합니다.')
    if column.endswith('_id') and column != 'article_id':
      if frame[column].str.len().gt(20).any():
        _invalid(name, f'{column}은 20자 이하여야 합니다.')
  for column in set(columns) & {'article_id', 'usage_code'}:
    bounds = (1, 2**63 - 1) if column == 'article_id' else (0, 2)
    frame[column] = _integers(name, column, frame[column], *bounds)
  key = ['article_id', 'category_id'] if name == 'result' else [columns[0]]
  _unique(name, frame, key)


def validate_tables(tables):
  '''내부 코드(0=사용, 1=비사용, 2=불확실)로 변환된 테이블을 검증한다.'''
  for name, columns in COLUMNS.items():
    if name not in tables:
      _invalid(name, '필수 테이블이 없습니다.')
    frame = tables[name]
    _validate_columns(name, frame, columns)

  for name, columns in [
    ('conflicts', ['conflict_name_en']),
    ('conflicts', ['conflict_name_ko']),
    ('categories', ['kind', 'category_name']),
    ('articles', ['conflict_id', 'article_url']),
  ]:
    _unique(name, tables[name], columns)
  categories = tables['categories']
  if not categories['kind'].isin(KIND_LABELS).all():
    _invalid('categories', 'kind는 wp 또는 tech여야 합니다.')
  for name in ('conflicts', 'categories'):
    if tables[name].empty:
      _invalid(name, '기준 테이블에 한 행 이상 필요합니다.')
  conflicts = tables['conflicts']
  if not conflicts['color'].astype(str).str.fullmatch(r'#[0-9a-fA-F]{6}').all():
    _invalid('conflicts', 'color는 #RRGGBB 형식이어야 합니다.')
  for column, bound in [('latitude', 90), ('longitude', 180)]:
    values = pd.to_numeric(conflicts[column], errors='coerce')
    if not values.between(-bound, bound).all():
      _invalid('conflicts', f'{column}은 {-bound}~{bound} 범위여야 합니다.')
    conflicts[column] = values.astype(float)

  articles = tables['articles']
  # 숫자를 나노초로 오인하지 않는다. 날짜 셀 또는 날짜 문자열만 허용한다.
  raw_dates = articles['published_date']
  if any(isinstance(value, (int, float)) for value in raw_dates):
    _invalid('articles', 'published_date를 YYYY-MM-DD 날짜 문자열로 입력해주세요.')
  try:
    dates = pd.to_datetime(raw_dates, errors='coerce', format='mixed')
  except (ValueError, TypeError):
    _invalid('articles', 'published_date에는 시간·시간대 없이 날짜만 입력해주세요.')
  if dates.isna().any() or not pd.api.types.is_datetime64_any_dtype(dates):
    _invalid('articles', 'published_date에 올바르지 않은 날짜가 있습니다.')
  if dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
    _invalid('articles', 'published_date에는 시간·시간대 없이 날짜만 입력해주세요.')
  articles['published_date'] = dates.astype('datetime64[ns]')
  for child, column, parent in [
    ('articles', 'conflict_id', 'conflicts'),
    ('result', 'article_id', 'articles'),
    ('result', 'category_id', 'categories'),
    ('sipri_dictionary', 'category_id', 'categories'),
    ('nato_dictionary', 'category_id', 'categories'),
  ]:
    if not tables[child][column].isin(tables[parent][column]).all():
      _invalid(child, f'{parent}에 없는 {column}을 참조합니다.')
  for name, kind in [('sipri_dictionary', 'wp'), ('nato_dictionary', 'tech')]:
    ids = categories.loc[categories['kind'].eq(kind), 'category_id']
    if not tables[name]['category_id'].isin(ids).all():
      _invalid(name, f'{kind} 유형의 범주만 참조해야 합니다.')
  results = tables['result']
  evidence = results.loc[results['usage_code'].eq(UsageCode.USED), 'evidence_sentence']
  if (evidence.isna() | evidence.astype(str).str.strip().eq('')).any():
    _invalid(
      'result', '사용 판정(내부 usage_code=0)에는 evidence_sentence가 필요합니다.'
    )
