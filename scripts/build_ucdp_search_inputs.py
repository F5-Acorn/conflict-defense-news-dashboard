'''검증된 UCDP 입력으로 각 분쟁의 전체 기간을 한 번에 조회할 GDELT 검색 계획을 생성한다.

검색 기간은 기사 발행일 기준이며, GDELT 처리 시각은 후보 검색용이다.
사건별 날짜·반경은 참고 정보이고 기사 채택의 필수 조건이 아니다.
'''

import argparse
import csv
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

if __package__:
  from .prepare_ucdp import METADATA_NAME, OUTPUT_COLUMNS
  from .ucdp_common import DEFAULT_ACTORS, PROJECT_ROOT, read_csv, sha256_file
else:
  from prepare_ucdp import METADATA_NAME, OUTPUT_COLUMNS
  from ucdp_common import DEFAULT_ACTORS, PROJECT_ROOT, read_csv, sha256_file

DEFAULT_METADATA = PROJECT_ROOT / 'data/ucdp/processed' / METADATA_NAME
DEFAULT_COUNTRY_CODES = PROJECT_ROOT / 'data/ucdp/references/country_code_mapping.csv'
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data/ucdp/processed'
FIPS_LOOKUP = PROJECT_ROOT / 'data/ucdp/references/gdelt_fips_countries.tsv'
NAME_COLUMNS = [
  'NameData',
  'NameOrig',
  'NameOrigFull',
  'NameOrigFullEng',
  'NewName',
  'NewNameFullMotherTongue',
  'NewNameFullEng',
]
OUTPUT_FILES = [
  'conflicts.csv',
  'actor_aliases.csv',
  'event_match_hints.csv',
  'gdelt_search_plan.json',
]


def load_events(metadata_path):
  metadata = json.loads(metadata_path.read_text(encoding='utf-8-sig'))
  if (
    metadata.get('schema_version') != 2
    or metadata.get('filters', {}).get('selection') != 'all_interstate'
  ):
    raise ValueError('새 prepare_ucdp.py로 국가 간 분쟁 입력을 먼저 생성하세요.')
  if not metadata.get('output_file') or not metadata.get('output_sha256'):
    raise ValueError('추출 결과 경로·해시가 없습니다.')
  path = (metadata_path.parent / metadata['output_file']).resolve()
  if sha256_file(path) != metadata['output_sha256']:
    raise ValueError('추출 CSV의 SHA-256이 JSON과 다릅니다.')
  events = read_csv(path, OUTPUT_COLUMNS, metadata['output_encoding'])
  if len(events) != metadata['output_rows']:
    raise ValueError('추출 CSV 행 수가 JSON과 다릅니다.')
  if events['id'].duplicated().any() or not events['type_of_violence'].eq('1').all():
    raise ValueError('추출 사건 ID 중복 또는 폭력 유형 오류입니다.')
  allowed = {'interstate_confirmed', 'interstate_reference', 'state_pair_candidate'}
  if not set(events['classification_status']) <= allowed:
    raise ValueError('검색 대상으로 승인되지 않은 사건 상태입니다.')
  for column in ['date_start', 'date_end']:
    dates = pd.to_datetime(events[column], format='mixed', errors='raise')
    if dates.isna().any():
      raise ValueError('사건 날짜가 비어 있습니다.')
    events[column] = dates.dt.strftime('%Y-%m-%d')
  return metadata, path, events


def load_country_codes(path, required_ids):
  frame = read_csv(
    path, ['ucdp_country_id', 'ucdp_country_name', 'gdelt_geo_country_code']
  )
  with FIPS_LOOKUP.open(encoding='utf-8-sig', newline='') as file:
    valid = dict(csv.reader(file, delimiter='\t'))
  unknown = set(frame['gdelt_geo_country_code']) - set(valid)
  if unknown:
    raise ValueError(f'GDELT 공식 위치 코드표에 없는 코드: {sorted(unknown)}')
  mapping = (
    frame.groupby('ucdp_country_id')['gdelt_geo_country_code']
    .agg(lambda x: sorted(set(x)))
    .to_dict()
  )
  missing = set(required_ids) - set(mapping)
  if missing:
    raise ValueError(f'국가코드 매핑을 추가해야 합니다: {sorted(missing, key=int)}')
  return mapping


def build_aliases(actors_path, events, targets, actor_encoding=None):
  if actor_encoding is None:
    try:
      actors_path.read_bytes().decode('utf-8-sig')
      actor_encoding = 'utf-8-sig'
    except UnicodeDecodeError:
      actor_encoding = 'cp1252'
  actors = read_csv(actors_path, ['ActorId', 'Version', *NAME_COLUMNS], actor_encoding)
  blank_rows = int(actors['ActorId'].str.strip().eq('').sum())
  actors = actors.loc[actors['ActorId'].str.strip().ne('')]
  if not actors['Version'].eq('26.1').all():
    raise ValueError('Actor 파일도 버전 26.1이어야 합니다.')

  # Actor의 활동 국가(GWNOLoc)는 행위자의 국적이 아니므로 매핑에 쓰지 않는다.
  aliases = {}
  canonical_names = {}

  def add(actor_id, value, source, needs_review=False):
    value = ' '.join(value.split())
    if not value or value.casefold() == 'n/a':
      return
    key = (actor_id, value.casefold())
    if key not in aliases:
      aliases[key] = {
        'actor_id': actor_id,
        'alias': value,
        'sources': set(),
        'needs_review': False,
      }
    aliases[key]['sources'].add(source)
    aliases[key]['needs_review'] |= needs_review or len(value) <= 3

  for side in ['a', 'b']:
    for actor_id, name in (
      events[[f'side_{side}_new_id', f'side_{side}']]
      .drop_duplicates()
      .itertuples(index=False, name=None)
    ):
      canonical_names.setdefault(actor_id, name)
      add(actor_id, name, f'GED.side_{side}')
      # 정부 명칭에서 국가 이름을 검색 후보로 추가한다. 연합 행위자는 분해하지 않는다.
      if name.startswith('Government of ') and ',' not in name:
        country_name = name.removeprefix('Government of ').split(' (', 1)[0]
        add(actor_id, country_name, 'derived_government_name', needs_review=True)

  used_ids = set(canonical_names) | {
    actor for target in targets for actor in target['actor_ids']
  }
  for row in actors.loc[actors['ActorId'].isin(used_ids)].to_dict('records'):
    canonical_names.setdefault(row['ActorId'], row['NameData'])
    name = row['NameData']
    if name.startswith('Government of ') and ',' not in name:
      add(
        row['ActorId'],
        name.removeprefix('Government of ').split(' (', 1)[0],
        'derived_government_name',
        needs_review=True,
      )
  missing_ids = sorted(used_ids - set(actors['ActorId']), key=int)
  for row in actors.loc[actors['ActorId'].isin(used_ids)].to_dict('records'):
    for column in NAME_COLUMNS:
      value = row[column]
      add(row['ActorId'], value, f'Actor.{column}')
      # 변경명 목록의 원문도 남기고, 분리한 검색어는 검토 대상으로 표시한다.
      if column.startswith('NewName') and ',' in value:
        for part in value.split(','):
          add(row['ActorId'], part, f'Actor.{column}.list_candidate', needs_review=True)

  records = []
  for key in sorted(aliases, key=lambda item: (int(item[0]), item[1])):
    record = aliases[key]
    records.append(
      {
        'actor_id': record['actor_id'],
        'canonical_name': canonical_names[record['actor_id']],
        'alias': record['alias'],
        'sources': '|'.join(sorted(record['sources'])),
        'needs_review': record['needs_review'] or record['actor_id'] in missing_ids,
        'actor_dataset_matched': record['actor_id'] not in missing_ids,
      }
    )
  return (
    pd.DataFrame(
      records,
      columns=[
        'actor_id',
        'canonical_name',
        'alias',
        'sources',
        'needs_review',
        'actor_dataset_matched',
      ],
    ),
    missing_ids,
    actor_encoding,
    blank_rows,
  )


def build_conflicts(targets, events, country_codes):
  records = []
  for target in targets:
    group = events.loc[events['conflict_id'].eq(target['conflict_id'])]
    countries = set(target['participant_country_ids']) | set(
      target['observed_country_ids']
    )
    records.append(
      {
        'conflict_id': target['conflict_id'],
        'ucdp_conflict_id': target['ucdp_conflict_id'],
        'conflict_name_en': target['conflict_name_en'],
        'scope_status': target['scope_status'],
        'analysis_start': target['analysis_start'],
        'analysis_end': target['analysis_end'],
        'annual_interstate_years': '|'.join(target['annual_interstate_years']),
        'actor_ids': '|'.join(target['actor_ids']),
        'actor_pairs': json.dumps(target['actor_pairs']),
        'participant_country_ids': '|'.join(target['participant_country_ids']),
        'observed_country_ids': '|'.join(target['observed_country_ids']),
        'gdelt_geo_country_codes': '|'.join(
          sorted({code for country in countries for code in country_codes[country]})
        ),
        'event_count': len(group),
        'first_observed_date': '' if group.empty else group['date_start'].min(),
        'last_observed_date': '' if group.empty else group['date_end'].max(),
      }
    )
  return pd.DataFrame(
    records,
    columns=[
      'conflict_id',
      'ucdp_conflict_id',
      'conflict_name_en',
      'scope_status',
      'analysis_start',
      'analysis_end',
      'annual_interstate_years',
      'actor_ids',
      'actor_pairs',
      'participant_country_ids',
      'observed_country_ids',
      'gdelt_geo_country_codes',
      'event_count',
      'first_observed_date',
      'last_observed_date',
    ],
  )


def build_hints(events, country_codes):
  hints = events.copy()
  hints['gdelt_geo_country_codes'] = hints['country_id'].map(
    lambda x: '|'.join(country_codes[x])
  )
  hints['hint_start_date'] = (
    pd.to_datetime(hints['date_start']) - pd.Timedelta(days=1)
  ).dt.strftime('%Y-%m-%d')
  hints['hint_end_date'] = (
    pd.to_datetime(hints['date_end']) + pd.Timedelta(days=3)
  ).dt.strftime('%Y-%m-%d')
  valid = pd.to_numeric(hints['latitude'], errors='coerce').between(
    -90, 90
  ) & pd.to_numeric(hints['longitude'], errors='coerce').between(-180, 180)
  precise = hints['where_prec'].isin(['1', '2']) & valid
  hints['spatial_hint_mode'] = 'country'
  hints.loc[hints['adm_1'].ne('') | hints['adm_2'].ne(''), 'spatial_hint_mode'] = (
    'administrative_area'
  )
  hints.loc[precise, 'spatial_hint_mode'] = 'radius'
  hints['hint_radius_km'] = ''
  hints.loc[precise & hints['where_prec'].eq('1'), 'hint_radius_km'] = '25'
  hints.loc[precise & hints['where_prec'].eq('2'), 'hint_radius_km'] = '50'
  hints['required_for_article_inclusion'] = False
  return hints


def build_batches(metadata, conflicts, aliases, events):
  records = []
  as_of_exclusive = date.fromisoformat(metadata['as_of']) + timedelta(days=1)
  extra = metadata['scope']['partition_extra_days']
  for conflict in conflicts.to_dict('records'):
    start, end = (
      date.fromisoformat(conflict[key]) for key in ['analysis_start', 'analysis_end']
    )
    end_exclusive = end + timedelta(days=1)
    mention_end = min(end_exclusive + timedelta(days=extra), as_of_exclusive)
    period_id = f'{start:%Y%m%d}_{end:%Y%m%d}'
    actor_ids = conflict['actor_ids'].split('|')
    terms = sorted(
      {
        name.casefold()
        for name in aliases.loc[aliases['actor_id'].isin(actor_ids), 'alias']
      }
    )
    group = events.loc[events['conflict_id'].eq(conflict['conflict_id'])]
    hint_count = int(
      (
        group['date_start'].lt(end_exclusive.isoformat())
        & group['date_end'].ge(start.isoformat())
      ).sum()
    )
    records.append(
      {
        'batch_id': f'{conflict["conflict_id"]}_{period_id}',
        'shared_period_query_id': period_id,
        'candidate_conflict_id': conflict['conflict_id'],
        'scope_status': conflict['scope_status'],
        'article_published_start': start.isoformat(),
        'article_published_end_exclusive': end_exclusive.isoformat(),
        'mention_start': start.isoformat(),
        'mention_end_exclusive': mention_end.isoformat(),
        # 과거 사건을 다룬 새 기사도 검색한다. SQLDATE를 기사 발행일로 쓰지 않는다.
        'event_partition_start': '2015-02-19',
        'event_partition_end_exclusive': mention_end.isoformat(),
        'gdelt_geo_country_codes': conflict['gdelt_geo_country_codes'].split('|')
        if conflict['gdelt_geo_country_codes']
        else [],
        'actor_ids': actor_ids,
        'actor_terms': terms,
        'actor_pairs': json.loads(conflict['actor_pairs']),
        'candidate_match_mode': 'geography_or_actor',
        'ucdp_hint_event_count': hint_count,
        'ucdp_event_match_required': False,
        'requires_article_conflict_review': True,
      }
    )
  return records


def build_search_inputs(
  metadata_path, actors_path, country_codes_path, output_dir, *, actor_encoding=None
):
  metadata_path, actors_path, country_codes_path, output_dir = (
    Path(p).resolve()
    for p in [metadata_path, actors_path, country_codes_path, output_dir]
  )
  metadata, events_path, events = load_events(metadata_path)
  if sha256_file(actors_path) != metadata['references']['actors']['sha256']:
    raise ValueError('Actor SHA-256이 전처리 때와 다릅니다. 전처리를 다시 실행하세요.')
  source_paths = {
    metadata_path,
    actors_path,
    country_codes_path,
    events_path,
    FIPS_LOOKUP,
  }
  if source_paths & {output_dir / name for name in OUTPUT_FILES}:
    raise ValueError('출력이 입력 파일을 덮어쓸 수 없습니다.')
  targets = metadata['targets']
  required = {
    x
    for t in targets
    for x in [*t['participant_country_ids'], *t['observed_country_ids']]
  }
  country_codes = load_country_codes(country_codes_path, required)
  aliases, missing, encoding, blank_rows = build_aliases(
    actors_path, events, targets, actor_encoding
  )
  conflicts = build_conflicts(targets, events, country_codes)
  hints = build_hints(events, country_codes)
  batches = build_batches(metadata, conflicts, aliases, events)
  output_dir.mkdir(parents=True, exist_ok=True)
  with TemporaryDirectory(prefix='.step3-', dir=output_dir) as temp_dir:
    temp, files = Path(temp_dir), {}
    for name, frame in [
      ('conflicts.csv', conflicts),
      ('actor_aliases.csv', aliases),
      ('event_match_hints.csv', hints),
    ]:
      frame.to_csv(temp / name, index=False, encoding='utf-8-sig')
      files[name] = {'rows': len(frame), 'sha256': sha256_file(temp / name)}
    plan = {
      'schema_version': 2,
      'generated_at_utc': datetime.now(UTC).isoformat(),
      'dataset_version': metadata['dataset_version'],
      'filters': metadata['filters'],
      'analysis_start': metadata['analysis_start'],
      'analysis_end': metadata['analysis_end'],
      'requested_analysis_end': metadata['scope']['analysis_end'],
      'as_of': metadata['as_of'],
      'annual_coverage_end': metadata['annual_coverage_end'],
      'candidate_coverage': metadata['candidate_coverage'],
      'candidate_missing_periods': metadata['candidate_missing_periods'],
      'coverage_note': metadata['coverage_note'],
      'sources': {
        name: {'path': str(path), 'sha256': sha256_file(path)}
        for name, path in [
          ('step2_metadata', metadata_path),
          ('events', events_path),
          ('actors', actors_path),
          ('country_codes', country_codes_path),
          ('gdelt_fips_lookup', FIPS_LOOKUP),
        ]
      },
      'actor_encoding': encoding,
      'actor_blank_id_rows_ignored': blank_rows,
      'missing_actor_ids': missing,
      'files': files,
      'counts': {
        'conflicts': len(conflicts),
        'events': len(events),
        'actors': aliases['actor_id'].nunique(),
        'aliases': len(aliases),
        'countries': len(required),
        'batches': len(batches),
        'unresolved_event_reviews': metadata['review_rows'],
      },
      'search_defaults': {
        'batch_coverage': 'full_conflict_analysis_period',
        'batch_time_basis': 'article_publication_period_with_mention_time_proxy',
        'partition_extra_days': metadata['scope']['partition_extra_days'],
        'event_match': 'optional_hint',
        'actor_match': 'candidate_only',
        'final_inclusion': 'article_evidence_of_direct_interstate_weapon_or_technology_use',
        'exclusions': [
          'intrastate_conflict',
          'non_state_conflict',
          'one_sided_violence',
          'support_only',
          'purchase_or_development_only',
        ],
      },
      'batches': batches,
    }
    (temp / 'gdelt_search_plan.json').write_text(
      json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    for name in OUTPUT_FILES:
      (temp / name).replace(output_dir / name)
  return plan


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--metadata', type=Path, default=DEFAULT_METADATA)
  parser.add_argument('--actors', type=Path, default=DEFAULT_ACTORS)
  parser.add_argument('--country-codes', type=Path, default=DEFAULT_COUNTRY_CODES)
  parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
  parser.add_argument('--actor-encoding')
  args = parser.parse_args()
  try:
    plan = build_search_inputs(
      args.metadata,
      args.actors,
      args.country_codes,
      args.output_dir,
      actor_encoding=args.actor_encoding,
    )
  except (OSError, ValueError, KeyError, LookupError) as error:
    parser.exit(1, f'검색 계획 생성 실패: {error}\n')
  print('생성 결과:', json.dumps(plan['counts'], ensure_ascii=False))
  print('저장 폴더:', args.output_dir.resolve())


if __name__ == '__main__':
  main()
