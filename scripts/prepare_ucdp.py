'''GED·ACD·Actor와 2026년 Candidate로 국가 간 분쟁 검색용 자료를 준비한다.

python scripts/prepare_ucdp.py [--scope ...] [--as-of YYYY-MM-DD]
원본은 보존하고 사건 목록·검토 목록·실행 기록을 생성한다.
국가 기반 폭력(type_of_violence=1)과 국가 간 분쟁(type_of_conflict=2)을 구분한다.
'''

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

if __package__:
  from .ucdp_common import (
    ANNUAL_END,
    DATASET_VERSION,
    DEFAULT_ACD,
    DEFAULT_ACTORS,
    DEFAULT_SCOPE,
    PROJECT_ROOT,
    InterstateClassifier,
    load_acd,
    load_actors,
    load_scope,
    sha256_file,
    split_ids,
  )
else:
  from ucdp_common import (
    ANNUAL_END,
    DATASET_VERSION,
    DEFAULT_ACD,
    DEFAULT_ACTORS,
    DEFAULT_SCOPE,
    PROJECT_ROOT,
    InterstateClassifier,
    load_acd,
    load_actors,
    load_scope,
    sha256_file,
    split_ids,
  )

DEFAULT_INPUT = PROJECT_ROOT / 'data/ucdp/raw/GEDEvent_v26_1.csv'
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data/ucdp/processed'
OUTPUT_NAME = 'ucdp_interstate_events.csv'
REVIEW_NAME = 'ucdp_event_review_queue.csv'
METADATA_NAME = 'ucdp_interstate_events.metadata.json'
SELECTED_COLUMNS = [
  'conflict_new_id',
  'conflict_name',
  'type_of_violence',
  'id',
  'dyad_new_id',
  'year',
  'date_start',
  'date_end',
  'date_prec',
  'country_id',
  'country',
  'adm_1',
  'adm_2',
  'latitude',
  'longitude',
  'where_prec',
  'side_a_new_id',
  'side_a',
  'side_b_new_id',
  'side_b',
  'active_year',
  'code_status',
  'gwnoa',
  'gwnob',
]
PROVENANCE_COLUMNS = ['source_kind', 'source_version', 'source_file']
DECISION_COLUMNS = [
  'conflict_id',
  'classification_status',
  'classification_reason',
  'needs_review',
]
OUTPUT_COLUMNS = [*SELECTED_COLUMNS, *PROVENANCE_COLUMNS, *DECISION_COLUMNS]


def source_record(path, **details):
  return {'path': str(path), 'sha256': sha256_file(path), **details}


def candidate_gaps(sources, start, end):
  '''공개분의 달력을 기준으로 공백을 기록한다. 사건 0건과 구분한다.'''
  cursor = max(start, ANNUAL_END + timedelta(days=1))
  gaps = []
  for source in sorted(sources, key=lambda s: s['coverage_start']):
    if source['kind'] != 'candidate':
      continue
    first, last = (
      date.fromisoformat(source[k]) for k in ['coverage_start', 'coverage_end']
    )
    if first > cursor and cursor <= end:
      gaps.append(
        {
          'start': cursor.isoformat(),
          'end': min(first - timedelta(days=1), end).isoformat(),
        }
      )
    cursor = max(cursor, last + timedelta(days=1))
  if cursor <= end:
    gaps.append({'start': cursor.isoformat(), 'end': end.isoformat()})
  return gaps


def build_targets(acd, events, scope, effective_end):
  start_year = date.fromisoformat(scope['analysis_start']).year
  relevant = acd.loc[
    acd['type_of_conflict'].eq('2')
    & pd.to_numeric(acd['year']).between(start_year, effective_end.year)
  ]
  ids = set(relevant['conflict_id']) | set(events['conflict_new_id'])
  targets = []
  for ucdp_id in sorted(ids, key=int):
    annual = acd.loc[acd['conflict_id'].eq(ucdp_id) & acd['type_of_conflict'].eq('2')]
    group = events.loc[events['conflict_new_id'].eq(ucdp_id)]
    actor_ids, participants, locations, pairs = (
      set(),
      set(),
      set(group['country_id']),
      set(),
    )
    for row in annual.to_dict('records'):
      a, b = split_ids(row['side_a_id']), split_ids(row['side_b_id'])
      actor_ids.update(a | b)
      for side in ['a', 'b']:
        if row[f'gwno_{side}'].strip():
          participants.update(split_ids(row[f'gwno_{side}']))
      pairs.update(tuple(sorted([x, y], key=int)) for x in a for y in b)
    for row in group.to_dict('records'):
      a, b = row['side_a_new_id'], row['side_b_new_id']
      actor_ids.update([a, b])
      pairs.add(tuple(sorted([a, b], key=int)))
      # gwnoa/gwnob는 해당 사건의 국가 행위자 정보. Actor.GWNOLoc과 다르다.
      for field in ['gwnoa', 'gwnob']:
        value = row[field].strip()
        if value and value != '0':
          participants.update(split_ids(value))
    name = (
      group['conflict_name'].iloc[0] if not group.empty else annual['location'].iloc[-1]
    )
    targets.append(
      {
        'conflict_id': f'ucdp_{ucdp_id}',
        'ucdp_conflict_id': ucdp_id,
        'conflict_name_en': name,
        'scope_status': 'acd_interstate'
        if not annual.empty
        else 'state_pair_candidate',
        'annual_interstate_years': sorted(annual['year'].unique(), key=int),
        'actor_ids': sorted(actor_ids, key=int),
        'actor_pairs': [list(pair) for pair in sorted(pairs)],
        'participant_country_ids': sorted(participants, key=int),
        'observed_country_ids': sorted(locations, key=int),
        'analysis_start': scope['analysis_start'],
        'analysis_end': effective_end.isoformat(),
        'event_count': len(group),
      }
    )
  return targets


def prepare_ucdp(
  input_path,
  output_dir,
  *,
  acd_path=DEFAULT_ACD,
  actors_path=DEFAULT_ACTORS,
  scope_path=DEFAULT_SCOPE,
  candidate_dir=None,
  chunksize=50_000,
  download_date=None,
  as_of=None,
):
  input_path, output_dir, acd_path, actors_path, scope_path = (
    Path(p).resolve()
    for p in [input_path, output_dir, acd_path, actors_path, scope_path]
  )
  if chunksize <= 0:
    raise ValueError('chunksize는 1 이상이어야 합니다.')
  scope = load_scope(scope_path)
  as_of = as_of or datetime.now(UTC).date()
  start = date.fromisoformat(scope['analysis_start'])
  end = min(date.fromisoformat(scope['analysis_end']), as_of)
  if end < start:
    raise ValueError('기준일이 분석 시작일보다 빠릅니다.')
  acd, (actors, actor_encoding, _) = load_acd(acd_path), load_actors(actors_path)
  classifier = InterstateClassifier(acd, actors)
  candidate_dir = Path(candidate_dir or input_path.parent).resolve()
  inputs = [
    (input_path, 'annual', DATASET_VERSION, '1989-01-01', ANNUAL_END.isoformat())
  ]
  for item in sorted(
    scope.get('candidate_sources', []), key=lambda s: s['coverage_end']
  ):
    if (
      date.fromisoformat(item['coverage_start']) <= end
      and date.fromisoformat(item['coverage_end']) >= start
    ):
      inputs.append(
        (
          candidate_dir / item['filename'],
          'candidate',
          item['version'],
          item['coverage_start'],
          item['coverage_end'],
        )
      )
  paths = {input_path, acd_path, actors_path, scope_path, *(item[0] for item in inputs)}
  if paths & {output_dir / name for name in [OUTPUT_NAME, REVIEW_NAME, METADATA_NAME]}:
    raise ValueError('출력이 입력 파일을 덮어쓸 수 없습니다.')

  parts, sources, input_rows = [], [], 0
  for path, kind, version, coverage_start, coverage_end in inputs:
    # 설정된 Candidate 파일이 없으면 실패한다. 2026년 전체를 확보한 것처럼 진행하지 않는다.
    header = pd.read_csv(path, nrows=0, encoding='utf-8-sig').columns
    missing = set(SELECTED_COLUMNS) - set(header)
    if missing:
      raise ValueError(f'{path.name} 필수 컬럼 누락: {sorted(missing)}')
    rows, source_ids = 0, set()
    with pd.read_csv(
      path,
      usecols=SELECTED_COLUMNS,
      dtype='string',
      keep_default_na=False,
      encoding='utf-8-sig',
      chunksize=chunksize,
    ) as chunks:
      for chunk in chunks:
        rows += len(chunk)
        years = pd.to_numeric(chunk['year'], errors='raise')
        types = pd.to_numeric(chunk['type_of_violence'], errors='raise')
        if years.isna().any() or types.isna().any():
          raise ValueError('year 또는 type_of_violence가 비어 있습니다.')
        # 중복 최신본 선택 전에 유형으로 거르지 않는다. 유형이 수정된 잠정 사건도 반영한다.
        chunk = chunk.loc[years.between(start.year, end.year)].copy()
        if chunk.empty:
          continue
        dates = {}
        for col in ['date_start', 'date_end']:
          dates[col] = pd.to_datetime(chunk[col], format='mixed', errors='raise')
          if dates[col].isna().any():
            raise ValueError(f'{col}가 비어 있습니다.')
        if dates['date_start'].gt(dates['date_end']).any():
          raise ValueError('사건 시작일이 종료일보다 늦습니다.')
        if (
          kind == 'candidate' and dates['date_start'].le(pd.Timestamp(ANNUAL_END)).any()
        ):
          raise ValueError(
            'Candidate에 연간 GED와 겹치는 사건이 있습니다. 갱신 규칙을 확인하세요.'
          )
        mask = dates['date_start'].le(pd.Timestamp(end)) & dates['date_end'].ge(
          pd.Timestamp(start)
        )
        chunk = chunk.loc[mask, SELECTED_COLUMNS].copy()
        if not chunk['id'].str.fullmatch(r'\d+').all():
          raise ValueError('사건 ID가 비어 있거나 잘못되었습니다.')
        if chunk['id'].duplicated().any() or set(chunk['id']) & source_ids:
          raise ValueError(f'{path.name} 내부의 사건 ID가 중복됩니다.')
        source_ids.update(chunk['id'])
        chunk['source_kind'], chunk['source_version'], chunk['source_file'] = (
          kind,
          version,
          path.name,
        )
        parts.append(chunk)
    input_rows += rows
    sources.append(
      source_record(
        path,
        kind=kind,
        version=version,
        rows=rows,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
      )
    )
  combined = (
    pd.concat(parts, ignore_index=True)
    if parts
    else pd.DataFrame(columns=[*SELECTED_COLUMNS, *PROVENANCE_COLUMNS])
  )
  before = len(combined)
  combined = combined.drop_duplicates('id', keep='last')
  duplicate_count = before - len(combined)
  selected, review, decisions = [], [], Counter()
  for row in combined.to_dict('records'):
    if row['type_of_violence'] != '1':
      decisions['excluded_non_state_based_violence'] += 1
      continue
    for key in [
      'conflict_new_id',
      'dyad_new_id',
      'country_id',
      'side_a_new_id',
      'side_b_new_id',
    ]:
      split_ids(row[key])
    status, reason = classifier.classify(row)
    decisions[reason] += 1
    row.update(
      {
        'conflict_id': f'ucdp_{row["conflict_new_id"]}',
        'classification_status': status,
        'classification_reason': reason,
        'needs_review': status != 'interstate_confirmed'
        or row['source_kind'] == 'candidate'
        or row['code_status'].casefold() != 'clear',
      }
    )
    if status == 'review':
      review.append(row)
    elif status != 'excluded':
      selected.append(row)
  events = pd.DataFrame(selected, columns=OUTPUT_COLUMNS)
  review_frame = pd.DataFrame(review, columns=OUTPUT_COLUMNS)
  targets = build_targets(acd, events, scope, end)
  output_dir.mkdir(parents=True, exist_ok=True)
  with TemporaryDirectory(prefix='.ucdp-', dir=output_dir) as temp_dir:
    temp = Path(temp_dir)
    events.to_csv(temp / OUTPUT_NAME, index=False, encoding='utf-8-sig')
    review_frame.to_csv(temp / REVIEW_NAME, index=False, encoding='utf-8-sig')
    files = {
      name: {'rows': len(frame), 'sha256': sha256_file(temp / name)}
      for name, frame in [(OUTPUT_NAME, events), (REVIEW_NAME, review_frame)]
    }
    metadata = {
      'schema_version': 2,
      'dataset': 'UCDP interstate news search inputs',
      'dataset_version': DATASET_VERSION,
      'processed_at_utc': datetime.now(UTC).isoformat(),
      'as_of': as_of.isoformat(),
      'download_date': download_date.isoformat() if download_date else None,
      'scope': scope,
      'analysis_start': start.isoformat(),
      'analysis_end': end.isoformat(),
      'annual_coverage_end': ANNUAL_END.isoformat(),
      'candidate_missing_periods': candidate_gaps(sources, start, end),
      'candidate_coverage': [
        {
          'start': s['coverage_start'],
          'end': s['coverage_end'],
          'version': s['version'],
        }
        for s in sources
        if s['kind'] == 'candidate'
      ],
      'coverage_note': '2026년은 잠정 자료이며 최신 공개분 이후의 신규 분쟁은 아직 포괄하지 않을 수 있음. GED 사건 없음은 기사 없음이 아님.',
      'filters': {
        'selection': scope['selection'],
        'type_of_violence': 1,
        'acd_type_of_conflict': 2,
      },
      'sources': sources,
      'references': {
        name: source_record(path)
        for name, path in [
          ('acd', acd_path),
          ('actors', actors_path),
          ('scope', scope_path),
        ]
      },
      'actor_encoding': actor_encoding,
      'input_rows': input_rows,
      'candidate_duplicate_rows_replaced': duplicate_count,
      'output_rows': len(events),
      'review_rows': len(review_frame),
      'classification_counts': dict(decisions),
      'conflict_count': len(targets),
      'country_count': events['country_id'].nunique(),
      'rows_by_year': {
        str(y): int(events['year'].eq(str(y)).sum())
        for y in range(start.year, end.year + 1)
      },
      'selected_columns': OUTPUT_COLUMNS,
      'output_file': OUTPUT_NAME,
      'output_sha256': files[OUTPUT_NAME]['sha256'],
      'output_encoding': 'utf-8-sig',
      'files': files,
      'targets': targets,
    }
    (temp / METADATA_NAME).write_text(
      json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    for name in [OUTPUT_NAME, REVIEW_NAME, METADATA_NAME]:
      (temp / name).replace(output_dir / name)
  return metadata


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
  parser.add_argument('--acd', type=Path, default=DEFAULT_ACD)
  parser.add_argument('--actors', type=Path, default=DEFAULT_ACTORS)
  parser.add_argument('--scope', type=Path, default=DEFAULT_SCOPE)
  parser.add_argument('--candidate-dir', type=Path)
  parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument('--chunksize', type=int, default=50_000)
  parser.add_argument('--download-date', type=date.fromisoformat)
  parser.add_argument(
    '--as-of', type=date.fromisoformat, help='조회 가능한 UTC 기준일. 기본 오늘'
  )
  args = parser.parse_args()
  try:
    metadata = prepare_ucdp(
      args.input,
      args.output_dir,
      acd_path=args.acd,
      actors_path=args.actors,
      scope_path=args.scope,
      candidate_dir=args.candidate_dir,
      chunksize=args.chunksize,
      download_date=args.download_date,
      as_of=args.as_of,
    )
  except (OSError, ValueError, KeyError) as error:
    parser.exit(1, f'추출 실패: {error}\n')
  print(
    f'검색 대상 {metadata["conflict_count"]}개 / 사건 {metadata["output_rows"]:,}건 / 별도 검토 {metadata["review_rows"]:,}건'
  )
  print(f'검색 기간: {metadata["analysis_start"]} ~ {metadata["analysis_end"]}')
  print('잠정 후보는 기사 본문에서 국가 간 직접 교전 여부를 검증해야 합니다.')
  print('실행 기록:', args.output_dir.resolve() / METADATA_NAME)


if __name__ == '__main__':
  main()
