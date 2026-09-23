'''선정된 12개 분쟁의 DB 적재용 7컬럼 CSV와 출처 메타데이터를 생성한다.'''

import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / 'data/ucdp/processed'
DEFAULT_REFERENCE = PROJECT_ROOT / 'data/ucdp/references/conflicts_table.json'
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data/final'
COLUMNS = [
  'conflict_id',
  'conflict_name_en',
  'conflict_name_ko',
  'color',
  'flag',
  'latitude',
  'longitude',
]
EXPECTED_COUNT = 12


def sha256(path):
  return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
  return json.loads(path.read_text(encoding='utf-8-sig'))


def read_rows(path):
  with path.open(encoding='utf-8-sig', newline='') as file:
    return list(csv.DictReader(file))


def index_rows(rows, key):
  indexed = {}
  for row in rows:
    value = row[key]
    if not value or value in indexed:
      raise ValueError(f'{key} 누락 또는 중복: {value}')
    indexed[value] = row
  return indexed


def coordinate(value, limit):
  try:
    number = Decimal(str(value))
    if not number.is_finite() or not -limit <= number <= limit:
      raise ValueError(f'좌표 범위 오류: {value}')
    if number != number.quantize(Decimal('0.000001')):
      raise ValueError(f'좌표는 소수점 6자리 이하여야 합니다: {value}')
    return f'{number:.6f}'
  except InvalidOperation as error:
    raise ValueError(f'잘못된 좌표: {value}') from error


def validate_table(rows):
  if len(rows) != EXPECTED_COUNT:
    raise ValueError(f'최종 분쟁은 {EXPECTED_COUNT}개여야 합니다.')
  for field in ['conflict_id', 'conflict_name_en', 'conflict_name_ko', 'color']:
    index_rows(rows, field)
  for row in rows:
    if list(row) != COLUMNS:
      raise ValueError('최종 컬럼은 첨부 ERD의 7개 컬럼이어야 합니다.')
    for field, limit in [
      ('conflict_id', 20),
      ('conflict_name_en', 100),
      ('conflict_name_ko', 100),
      ('flag', 30),
    ]:
      value = row[field]
      if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{field} 누락 또는 길이 오류: {value}')
      if value != value.strip() or any(c in value for c in '\r\n\t'):
        raise ValueError(f'{field} 공백·제어문자 오류: {value}')
    if not re.fullmatch(r'ucdp_[0-9]+', row['conflict_id']):
      raise ValueError('UCDP 기반 분쟁 ID가 아닙니다.')
    if row['conflict_name_en'].upper().startswith('XXX'):
      raise ValueError('미정 영문 분쟁명을 사용할 수 없습니다.')
    if not re.fullmatch(r'#[0-9A-F]{6}', row['color']):
      raise ValueError('색상은 대문자 #RRGGBB 형식이어야 합니다.')
    if not re.fullmatch(r'[🇦-🇿]{2}( [🇦-🇿]{2})*', row['flag']):
      raise ValueError('국기는 국가별 이모지를 공백으로 연결해야 합니다.')
    coordinate(row['latitude'], 90)
    coordinate(row['longitude'], 180)


def build_conflicts_table(
  source_dir=DEFAULT_SOURCE_DIR,
  reference_path=DEFAULT_REFERENCE,
  output_dir=DEFAULT_OUTPUT_DIR,
):
  source_dir, reference_path, output_dir = (
    Path(path).resolve() for path in [source_dir, reference_path, output_dir]
  )
  paths = {
    'conflicts': source_dir / 'conflicts.csv',
    'events': source_dir / 'ucdp_interstate_events.csv',
    'event_metadata': source_dir / 'ucdp_interstate_events.metadata.json',
    'search_plan': source_dir / 'gdelt_search_plan.json',
    'display_reference': reference_path,
  }
  if set(paths.values()) & {
    output_dir / 'conflicts.csv',
    output_dir / 'conflicts.metadata.json',
  }:
    raise ValueError('최종 출력으로 검색용 입력을 덮어쓸 수 없습니다.')
  reference = read_json(reference_path)
  plan = read_json(paths['search_plan'])
  event_metadata = read_json(paths['event_metadata'])
  if (
    reference['schema_version'] != 1
    or reference['selection'] != 'fixed_acd_interstate_ids'
    or plan['schema_version'] != 2
    or plan['filters']['selection'] != 'all_interstate'
    or plan['as_of'] != reference['source_as_of']
    or event_metadata['as_of'] != reference['source_as_of']
  ):
    raise ValueError('기준일·입력 버전·대상 선정 설정을 확인하세요.')
  hashes = {name: sha256(path) for name, path in paths.items()}
  expected_hashes = {
    'conflicts': plan['files']['conflicts.csv']['sha256'],
    'events': plan['sources']['events']['sha256'],
    'event_metadata': plan['sources']['step2_metadata']['sha256'],
  }
  if any(hashes[name] != expected for name, expected in expected_hashes.items()):
    raise ValueError('입력 SHA-256이 검색 계획과 다릅니다. 입력을 재생성하세요.')
  if hashes['events'] != event_metadata['output_sha256']:
    raise ValueError('사건 CSV의 SHA-256이 사건 메타데이터와 다릅니다.')

  source = index_rows(read_rows(paths['conflicts']), 'conflict_id')
  events = index_rows(read_rows(paths['events']), 'id')
  records = index_rows(reference['records'], 'conflict_id')
  if (
    len(source) != plan['files']['conflicts.csv']['rows']
    or len(events) != event_metadata['output_rows']
  ):
    raise ValueError('입력 행 수가 메타데이터와 다릅니다.')
  selected_ids = {
    key for key, row in source.items() if row['scope_status'] == 'acd_interstate'
  }
  if len(records) != EXPECTED_COUNT or set(records) != selected_ids:
    raise ValueError('참조 파일은 ACD 대상 12개와 정확히 일치해야 합니다.')

  rows, provenance = [], []
  for conflict_id in sorted(records, key=lambda key: int(key.removeprefix('ucdp_'))):
    record, conflict = records[conflict_id], source[conflict_id]
    event = events.get(record['location_event_id'])
    if event is None:
      raise ValueError(f'{conflict_id}: 대표 좌표의 근거 사건이 없습니다.')
    mode = record['location_mode']
    if mode == 'conflict_event_reference':
      if event['conflict_id'] != conflict_id:
        raise ValueError(f'{conflict_id}: 다른 분쟁 사건의 좌표입니다.')
    elif mode == 'regional_reference':
      if int(conflict['event_count']) != 0:
        raise ValueError(f'{conflict_id}: 지역 대표점 예외는 사건 0건에만 적용합니다.')
      if event['country_id'] not in conflict['participant_country_ids'].split('|'):
        raise ValueError(f'{conflict_id}: 교전국 밖의 지역 대표점입니다.')
    else:
      raise ValueError(f'{conflict_id}: 알 수 없는 대표 위치 선정 방식입니다.')
    if event['classification_status'] not in {
      'interstate_confirmed',
      'interstate_reference',
    }:
      raise ValueError(f'{conflict_id}: 잠정 후보 사건 좌표를 사용할 수 없습니다.')
    if not record['location_label'].strip() or not record['location_note'].strip():
      raise ValueError(f'{conflict_id}: 대표 위치 이름과 선정 근거가 필요합니다.')
    row = {
      'conflict_id': conflict_id,
      'conflict_name_en': conflict['conflict_name_en'],
      'conflict_name_ko': record['conflict_name_ko'],
      'color': record['color'],
      'flag': record['flag'],
      'latitude': coordinate(event['latitude'], 90),
      'longitude': coordinate(event['longitude'], 180),
    }
    rows.append(row)
    provenance.append(
      {
        **row,
        'scope_status': conflict['scope_status'],
        'annual_interstate_years': conflict['annual_interstate_years'].split('|'),
        'source_event_count': int(conflict['event_count']),
        'participant_country_ids': conflict['participant_country_ids'].split('|'),
        'location_mode': mode,
        'location_label': record['location_label'],
        'location_note': record['location_note'],
        'location_event': {
          key: event[key]
          for key in [
            'id',
            'conflict_id',
            'year',
            'country_id',
            'country',
            'adm_1',
            'adm_2',
            'where_prec',
            'classification_status',
            'source_kind',
            'source_version',
          ]
        },
      }
    )
  validate_table(rows)
  metadata = {
    'schema_version': 1,
    'table': 'conflicts',
    'columns': COLUMNS,
    'row_count': len(rows),
    'as_of': plan['as_of'],
    'dataset_version': plan['dataset_version'],
    'analysis_start': plan['analysis_start'],
    'analysis_end': plan['analysis_end'],
    'annual_coverage_end': plan['annual_coverage_end'],
    'candidate_coverage': plan['candidate_coverage'],
    'candidate_missing_periods': plan['candidate_missing_periods'],
    'selection': reference['selection'],
    'location_semantics': reference['location_semantics'],
    'location_selection_policy': reference['location_selection_policy'],
    'sources': {
      name: {'filename': path.name, 'sha256': hashes[name]}
      for name, path in paths.items()
    },
    'excluded': [
      {
        'conflict_id': key,
        'conflict_name_en': row['conflict_name_en'],
        'scope_status': row['scope_status'],
        'reason': '사용자가 최종 테이블을 ACD 대상 12개로 한정하여 제외',
      }
      for key, row in source.items()
      if key not in records
    ],
    'records': provenance,
  }
  output_dir.mkdir(parents=True, exist_ok=True)
  with TemporaryDirectory(prefix='.conflicts-', dir=output_dir) as temp_dir:
    temp = Path(temp_dir)
    with (temp / 'conflicts.csv').open('w', encoding='utf-8-sig', newline='') as file:
      writer = csv.DictWriter(file, fieldnames=COLUMNS, lineterminator='\n')
      writer.writeheader()
      writer.writerows(rows)
    metadata['output_sha256'] = sha256(temp / 'conflicts.csv')
    (temp / 'conflicts.metadata.json').write_text(
      json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    for name in ['conflicts.csv', 'conflicts.metadata.json']:
      (temp / name).replace(output_dir / name)
  return metadata


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source-dir', type=Path, default=DEFAULT_SOURCE_DIR)
  parser.add_argument('--reference', type=Path, default=DEFAULT_REFERENCE)
  parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
  args = parser.parse_args()
  metadata = build_conflicts_table(args.source_dir, args.reference, args.output_dir)
  print(f'conflicts: {metadata["row_count"]}행, {len(COLUMNS)}컬럼 → {args.output_dir}')


if __name__ == '__main__':
  main()
