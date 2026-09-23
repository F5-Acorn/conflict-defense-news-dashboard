'''DB 연결 전 dummy 엑셀을 읽고 집계에 필요한 관계와 값을 검증한다.'''

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from data.reference_data import KIND_LABELS

DUMMY_DIR = Path(__file__).resolve().parent / 'dummy'
FILES = {
  'conflicts': ('conflicts.xlsx', 'conflicts'),
  'categories': ('categories.xlsm', 'categories'),
  'sipri_dictionary': ('SIPRI_dictionary.xlsx', 'Sheet1'),
  'nato_dictionary': ('NATO_dictionary.xlsx', 'NATO_dictionary'),
  'usage_patterns': ('usage_patterns.xlsx', 'Sheet1'),
  'articles': ('article_example.xlsx', 'articles'),
  'result': ('result_example.xlsx', 'result'),
}
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
  'usage_patterns': ['pattern_id', 'base_form', 'trans_form'],
  'articles': ['article_id', 'conflict_id', 'published_date', 'article_url', 'title'],
  'result': ['article_id', 'category_id', 'usage_code', 'evidence_sentence'],
}


class DataValidationError(ValueError):
  '''사용자가 원본 파일에서 수정할 수 있는 데이터 오류.'''


def file_payloads(directory=None):
  '''파일 전체 내용으로 캐시를 구분한다. 수정 시각이 같아도 변경을 감지한다.'''
  directory = Path(directory) if directory is not None else DUMMY_DIR
  payloads = []
  for name, (filename, _) in FILES.items():
    try:
      payloads.append((name, (directory / filename).read_bytes()))
    except OSError as exc:
      raise DataValidationError(f'{filename}: 파일을 읽을 수 없습니다. {exc}') from exc
  return tuple(payloads)


def _invalid(name, message):
  raise DataValidationError(f'{FILES[name][0]}: {message}')


def _unique(name, frame, columns):
  if frame.duplicated(columns).any():
    _invalid(name, f'{", ".join(columns)} 값이 중복되었습니다.')


def validate_tables(tables):
  '''집계 오류는 거부하고, 기존 사전·사용 표현의 정제 과제는 원본대로 보존한다.'''
  for name, columns in COLUMNS.items():
    frame = tables[name]
    missing = set(columns) - set(frame.columns)
    if missing:
      _invalid(name, f'필수 컬럼이 없습니다: {", ".join(sorted(missing))}')
    nullable = {'flag', 'evidence_sentence'}
    if name == 'usage_patterns':
      nullable.add('trans_form')
    for column in columns:
      if column not in nullable:
        blank = frame[column].isna() | frame[column].astype(str).str.strip().eq('')
        if blank.any():
          _invalid(name, f'{column}에 빈값이 있습니다 (엑셀 {blank.idxmax() + 2}행).')
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
      numeric = pd.to_numeric(frame[column], errors='coerce')
      invalid = numeric.isna() | numeric.mod(1).ne(0)
      if column == 'article_id':
        invalid |= numeric.le(0) | numeric.ge(2**63)
      else:
        invalid |= ~numeric.isin([0, 1, 2])
      if invalid.any():
        _invalid(name, f'{column} 값이 올바른 정수 범위가 아닙니다.')
      frame[column] = numeric.astype('int64')
    key = ['article_id', 'category_id'] if name == 'result' else [columns[0]]
    _unique(name, frame, key)

  for name, columns in [
    ('conflicts', ['conflict_name_en']),
    ('conflicts', ['conflict_name_ko']),
    ('categories', ['kind', 'category_name']),
    ('articles', ['article_url']),
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
    _invalid('articles', 'published_date를 엑셀 날짜 또는 YYYY-MM-DD로 입력해주세요.')
  dates = pd.to_datetime(raw_dates, errors='coerce', format='mixed')
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
  evidence = results.loc[results['usage_code'].eq(1), 'evidence_sentence']
  if (evidence.isna() | evidence.astype(str).str.strip().eq('')).any():
    _invalid('result', 'usage_code=1인 결과에는 evidence_sentence가 필요합니다.')


@st.cache_data(show_spinner=False, max_entries=4)
def read_tables(payloads):
  tables = {}
  for name, content in payloads:
    filename, sheet = FILES[name]
    try:
      tables[name] = pd.read_excel(
        BytesIO(content), sheet_name=sheet, engine='openpyxl'
      )
    except Exception as exc:
      raise DataValidationError(
        f'{filename}: {sheet} 시트를 읽을 수 없습니다. {exc}'
      ) from exc
  validate_tables(tables)
  return {name: frame[COLUMNS[name]].copy() for name, frame in tables.items()}


def load_tables(directory=None):
  '''7개 테이블을 반환한다. 호출자의 수정은 캐시 원본에 영향을 주지 않는다.'''
  return read_tables(file_payloads(directory))
