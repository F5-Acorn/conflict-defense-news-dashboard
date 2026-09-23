'''UCDP 원본·수집 범위·국가 간 분쟁 분류의 공통 규칙.'''

import hashlib
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCOPE = PROJECT_ROOT / 'data/ucdp/references/collection_scope.json'
DEFAULT_ACD = PROJECT_ROOT / 'data/ucdp/raw/UcdpPrioConflict_v26_1.csv'
DEFAULT_ACTORS = PROJECT_ROOT / 'data/ucdp/raw/Actor_v26_1.csv'
DATASET_VERSION = '26.1'
ANNUAL_END = date(2025, 12, 31)


def sha256_file(path):
  with Path(path).open('rb') as file:
    return hashlib.file_digest(file, 'sha256').hexdigest()


def read_csv(path, required, encoding='utf-8-sig'):
  frame = pd.read_csv(path, dtype='string', keep_default_na=False, encoding=encoding)
  missing = set(required) - set(frame.columns)
  if missing:
    raise ValueError(f'{Path(path).name}에 필요한 컬럼이 없습니다: {sorted(missing)}')
  return frame


def split_ids(value):
  values = [part.strip() for part in str(value).split(',') if part.strip()]
  if not values or any(not re.fullmatch(r'\d+', part) for part in values):
    raise ValueError(f'잘못된 ID 목록: {value!r}')
  return set(values)


def load_scope(path):
  scope = json.loads(Path(path).read_text(encoding='utf-8-sig'))
  if (
    scope.get('schema_version') != 1
    or scope.get('dataset_version') != DATASET_VERSION
    or scope.get('selection') != 'all_interstate'
  ):
    raise ValueError(
      '수집 설정은 schema_version=1, GED 26.1, all_interstate여야 합니다.'
    )
  start, end = (
    date.fromisoformat(scope[key]) for key in ['analysis_start', 'analysis_end']
  )
  if start > end or start < date(2015, 2, 19):
    raise ValueError(
      '검색 기간은 GDELT 2.0 시작 이후이며 시작일 <= 종료일이어야 합니다.'
    )
  extra = scope.get('partition_extra_days')
  if type(extra) is not int or not 0 <= extra <= 365:
    raise ValueError('partition_extra_days는 0~365 정수여야 합니다.')
  seen = set()
  for source in scope.get('candidate_sources', []):
    name = source['filename']
    if Path(name).name != name or name in seen:
      raise ValueError('Candidate 파일명은 중복 없는 단일 파일명이어야 합니다.')
    seen.add(name)
    first, last = (
      date.fromisoformat(source[k]) for k in ['coverage_start', 'coverage_end']
    )
    if first > last or first <= ANNUAL_END or not source.get('version'):
      raise ValueError(
        'Candidate 기간·버전을 확인하세요. 연간 GED 이후 자료만 연결합니다.'
      )
  return scope


def load_actors(path, encoding=None):
  if encoding is None:
    try:
      Path(path).read_bytes().decode('utf-8-sig')
      encoding = 'utf-8-sig'
    except UnicodeDecodeError:
      encoding = 'cp1252'
  actors = read_csv(path, ['ActorId', 'NameData', 'Org', 'Version'], encoding)
  blank = int(actors['ActorId'].str.strip().eq('').sum())
  actors = actors.loc[actors['ActorId'].str.strip().ne('')].copy()
  if not actors['Version'].eq(DATASET_VERSION).all():
    raise ValueError('Actor 파일 버전은 26.1이어야 합니다.')
  if actors['ActorId'].duplicated().any():
    raise ValueError('Actor ID가 중복됩니다.')
  return actors, encoding, blank


def load_acd(path):
  frame = read_csv(
    path,
    [
      'conflict_id',
      'year',
      'type_of_conflict',
      'side_a_id',
      'side_b_id',
      'side_a',
      'side_b',
      'gwno_a',
      'gwno_b',
      'location',
      'version',
    ],
  )
  if not frame['version'].eq(DATASET_VERSION).all():
    raise ValueError('Armed Conflict Dataset 버전은 26.1이어야 합니다.')
  if frame.duplicated(['conflict_id', 'year']).any():
    raise ValueError('ACD 분쟁 ID·연도가 중복됩니다.')
  for row in frame.to_dict('records'):
    split_ids(row['conflict_id'])
    int(row['year'])
    if row['type_of_conflict'] not in {'1', '2', '3', '4'}:
      raise ValueError('알 수 없는 ACD 분쟁 유형입니다.')
    row_ids = ['side_a_id', 'side_b_id']
    for key in row_ids:
      split_ids(row[key])
  return frame


class InterstateClassifier:
  '''동일 연도 분류 우선. 연도 누락과 신규 국가 쌍은 확정값과 구분한다.'''

  def __init__(self, acd, actors):
    self.by_year = {(r['conflict_id'], r['year']): r for r in acd.to_dict('records')}
    self.interstate = {}
    for row in acd.loc[acd['type_of_conflict'].eq('2')].to_dict('records'):
      self.interstate.setdefault(row['conflict_id'], []).append(row)
    self.known_actors = set(actors['ActorId'])
    # Actor 코드북 Org=4: Government. 이름 문자열로 국가를 추정하지 않는다.
    self.state_actors = set(actors.loc[actors['Org'].eq('4'), 'ActorId'])

  @staticmethod
  def matches(row, side_a, side_b):
    left, right = split_ids(row['side_a_id']), split_ids(row['side_b_id'])
    return (side_a in left and side_b in right) or (side_b in left and side_a in right)

  def classify(self, event):
    a, b = event['side_a_new_id'], event['side_b_new_id']
    if a == b:
      return 'review', 'same_actor_on_both_sides'
    exact = self.by_year.get((event['conflict_new_id'], event['year']))
    if exact is not None:
      if exact['type_of_conflict'] != '2':
        return 'excluded', 'acd_non_interstate_year'
      if self.matches(exact, a, b):
        return 'interstate_confirmed', 'acd_same_year_and_parties'
      return 'review', 'acd_party_mismatch'
    for row in self.interstate.get(event['conflict_new_id'], []):
      if self.matches(row, a, b):
        return 'interstate_reference', 'acd_other_year_and_parties'
    if a in self.state_actors and b in self.state_actors:
      return 'state_pair_candidate', 'government_pair_without_annual_classification'
    if a not in self.known_actors or b not in self.known_actors:
      return 'review', 'unknown_actor'
    return 'excluded', 'non_government_pair'
