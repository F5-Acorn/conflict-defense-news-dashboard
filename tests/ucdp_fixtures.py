'''작은 합성 UCDP 자료. 실제 분쟁 판단과 외부 다운로드에 의존하지 않는다.'''

import csv
import json
from datetime import date

from scripts.build_ucdp_search_inputs import NAME_COLUMNS
from scripts.prepare_ucdp import SELECTED_COLUMNS, prepare_ucdp


def write_csv(path, columns, rows, encoding='utf-8-sig'):
  with path.open('w', encoding=encoding, newline='') as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows({key: row.get(key, '') for key in columns} for row in rows)


def event(id='1', **updates):
  row = dict.fromkeys(SELECTED_COLUMNS, '')
  row.update(
    {
      'id': id,
      'year': '2025',
      'type_of_violence': '1',
      'active_year': '1',
      'code_status': 'Clear',
      'conflict_new_id': '10',
      'conflict_name': 'A - B',
      'dyad_new_id': '100',
      'side_a_new_id': '1',
      'side_b_new_id': '2',
      'side_a': 'Government of Alpha',
      'side_b': 'Government of Beta',
      'country_id': '369',
      'country': 'Ukraine',
      'gwnoa': '365',
      'gwnob': '369',
      'date_start': '2025-12-20 00:00:00.000',
      'date_end': '2025-12-20 00:00:00.000',
      'date_prec': '1',
      'where_prec': '1',
      'latitude': '50.450000',
      'longitude': '30.523330',
      'adm_1': 'Kyiv',
    }
  )
  row.update(updates)
  return row


def acd_row(**updates):
  row = {
    'conflict_id': '10',
    'year': '2025',
    'type_of_conflict': '2',
    'side_a_id': '1',
    'side_b_id': '2',
    'side_a': 'Government of Alpha',
    'side_b': 'Government of Beta',
    'gwno_a': '365',
    'gwno_b': '369',
    'location': 'Alpha, Beta',
    'version': '26.1',
  }
  row.update(updates)
  return row


class Inputs:
  def __init__(self, root):
    self.root = root
    self.ged = root / 'ged.csv'
    self.acd = root / 'acd.csv'
    self.actors = root / 'actors.csv'
    self.scope_path = root / 'scope.json'
    self.output = root / 'processed'
    self.scope = {
      'schema_version': 1,
      'dataset_version': '26.1',
      'selection': 'all_interstate',
      'analysis_start': '2025-12-15',
      'analysis_end': '2026-12-31',
      'partition_extra_days': 14,
      'candidate_sources': [],
    }
    self.write_events([event()])
    self.write_acd([acd_row()])
    write_csv(
      self.actors,
      ['ActorId', 'Version', 'Org', *NAME_COLUMNS],
      [
        {
          'ActorId': '1',
          'Version': '26.1',
          'Org': '4',
          'NameData': 'Government of Alpha',
        },
        {
          'ActorId': '2',
          'Version': '26.1',
          'Org': '4',
          'NameData': 'Government of Beta',
          'NameOrigFullEng': 'Groupe café, original',
          'NewName': 'Beta, B',
        },
        {'ActorId': '3', 'Version': '26.1', 'Org': '1', 'NameData': 'Rebels'},
        {
          'ActorId': '4',
          'Version': '26.1',
          'Org': '4',
          'NameData': 'Government of Gamma',
        },
        {},
      ],
      'cp1252',
    )
    self.save_scope()

  def save_scope(self):
    self.scope_path.write_text(json.dumps(self.scope), encoding='utf-8')

  def write_events(self, rows):
    write_csv(self.ged, SELECTED_COLUMNS, rows)

  def write_acd(self, rows):
    write_csv(self.acd, list(acd_row()), rows)

  def add_candidate(self, name, rows, start='2026-01-01', end='2026-01-31'):
    write_csv(self.root / name, SELECTED_COLUMNS, rows)
    self.scope['candidate_sources'].append(
      {'filename': name, 'version': name, 'coverage_start': start, 'coverage_end': end}
    )
    self.save_scope()

  def run(self, **kwargs):
    return prepare_ucdp(
      self.ged,
      self.output,
      acd_path=self.acd,
      actors_path=self.actors,
      scope_path=self.scope_path,
      as_of=date(2026, 2, 15),
      **kwargs,
    )

  def read(self, name):
    with (self.output / name).open(encoding='utf-8-sig') as file:
      return list(csv.DictReader(file))
