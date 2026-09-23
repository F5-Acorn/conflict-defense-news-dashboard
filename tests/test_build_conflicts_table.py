'''최종 12개 분쟁의 범위·ERD 일치·출처·재현성과 잘못된 입력의 거부를 검사한다.'''

import copy
import json
import re
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_conflicts_table import (
  COLUMNS,
  DEFAULT_OUTPUT_DIR,
  DEFAULT_REFERENCE,
  DEFAULT_SOURCE_DIR,
  PROJECT_ROOT,
  build_conflicts_table,
  read_json,
  read_rows,
  sha256,
  validate_table,
)

EXPECTED_IDS = {
  'ucdp_218',
  'ucdp_274',
  'ucdp_294',
  'ucdp_302',
  'ucdp_324',
  'ucdp_409',
  'ucdp_11639',
  'ucdp_13243',
  'ucdp_13324',
  'ucdp_14609',
  'ucdp_16099',
  'ucdp_16470',
}


class BuildConflictsTableTest(unittest.TestCase):
  def setUp(self):
    temp = TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    self.root = Path(temp.name)
    self.output = self.root / 'final'
    self.reference_path = self.root / 'reference.json'
    self.reference = read_json(DEFAULT_REFERENCE)
    self.save_reference()

  def save_reference(self):
    self.reference_path.write_text(
      json.dumps(self.reference, ensure_ascii=False), encoding='utf-8'
    )

  def build(self, source_dir=DEFAULT_SOURCE_DIR):
    return build_conflicts_table(source_dir, self.reference_path, self.output)

  def test_snapshot_matches_erd_and_is_reproducible(self):
    # 기본 참조 파일을 사용해야 출처 파일의 해시도 저장본과 일치한다.
    metadata = build_conflicts_table(output_dir=self.output)
    rows = read_rows(self.output / 'conflicts.csv')
    self.assertEqual(len(rows), 12)
    self.assertEqual(list(rows[0]), COLUMNS)
    self.assertEqual({row['conflict_id'] for row in rows}, EXPECTED_IDS)
    self.assertEqual(len(metadata['excluded']), 3)
    self.assertEqual(metadata['output_sha256'], sha256(self.output / 'conflicts.csv'))
    schema = (PROJECT_ROOT / 'schema.dbml').read_text()
    # 선택적인 checks 블록이 없어도 다음 테이블 컬럼까지 읽지 않는다.
    block = schema.split('Table conflicts {', 1)[1].split('\n}', 1)[0]
    columns = re.findall(r'^  (\w+) (?:varchar|char|decimal)\(', block, re.MULTILINE)
    self.assertEqual(columns, COLUMNS)
    original = {
      name: (self.output / name).read_bytes()
      for name in ['conflicts.csv', 'conflicts.metadata.json']
    }
    build_conflicts_table(output_dir=self.output)
    for name, expected in original.items():
      self.assertEqual((self.output / name).read_bytes(), expected)
      self.assertEqual((DEFAULT_OUTPUT_DIR / name).read_bytes(), expected)

  def test_provenance_keeps_zero_event_and_provisional_coordinate_explicit(self):
    metadata = self.build()
    records = {row['conflict_id']: row for row in metadata['records']}
    regional = records['ucdp_16099']
    self.assertEqual(regional['source_event_count'], 0)
    self.assertEqual(regional['location_mode'], 'regional_reference')
    self.assertEqual(regional['location_event']['conflict_id'], 'ucdp_16470')
    self.assertEqual(regional['location_event']['id'], '580798')
    iran_iraq = records['ucdp_324']['location_event']
    self.assertEqual(iran_iraq['source_kind'], 'candidate')
    self.assertEqual(iran_iraq['classification_status'], 'interstate_reference')
    self.assertEqual(records['ucdp_409']['location_event']['where_prec'], '5')

  def test_candidates_missing_targets_and_invalid_location_links_are_rejected(self):
    initial = copy.deepcopy(self.reference)
    changes = [
      ('잠정 후보 포함', lambda ref: ref['records'][0].update(conflict_id='ucdp_164')),
      ('분쟁 누락', lambda ref: ref['records'].pop()),
      ('중복 ID', lambda ref: ref['records'].append(ref['records'][0])),
      ('기준일 변경', lambda ref: ref.update(source_as_of='2026-09-24')),
      (
        '다른 분쟁 좌표',
        lambda ref: ref['records'][0].update(location_event_id='584790'),
      ),
      ('근거 없는 좌표', lambda ref: ref['records'][0].update(location_event_id='0')),
      ('근거 누락', lambda ref: ref['records'][0].update(location_note='')),
      (
        '교전국 밖 대표점',
        lambda ref: ref['records'][10].update(location_event_id='563005'),
      ),
    ]
    for label, change in changes:
      with self.subTest(label=label):
        self.reference = copy.deepcopy(initial)
        change(self.reference)
        self.save_reference()
        with self.assertRaises(ValueError):
          self.build()
        self.assertFalse(self.output.exists())

  def test_changed_source_preserves_previous_output(self):
    self.build()
    before = {
      path.name: path.read_bytes() for path in self.output.iterdir() if path.is_file()
    }
    source_dir = self.root / 'source'
    source_dir.mkdir()
    for name in [
      'conflicts.csv',
      'ucdp_interstate_events.metadata.json',
      'gdelt_search_plan.json',
    ]:
      shutil.copyfile(DEFAULT_SOURCE_DIR / name, source_dir / name)
    (source_dir / 'ucdp_interstate_events.csv').symlink_to(
      DEFAULT_SOURCE_DIR / 'ucdp_interstate_events.csv'
    )
    with (source_dir / 'conflicts.csv').open('a', encoding='utf-8') as file:
      file.write('\n')
    with self.assertRaisesRegex(ValueError, 'SHA-256'):
      self.build(source_dir)
    self.assertEqual(
      before, {name: (self.output / name).read_bytes() for name in before}
    )

  def test_search_input_cannot_be_overwritten(self):
    with self.assertRaisesRegex(ValueError, '덮어쓸'):
      build_conflicts_table(output_dir=DEFAULT_SOURCE_DIR)

  def test_field_constraints_reject_bad_import_data(self):
    original = read_rows(DEFAULT_OUTPUT_DIR / 'conflicts.csv')
    changes = [
      {'conflict_name_ko': ''},
      {'conflict_name_en': 'XXX2'},
      {'conflict_name_en': 'a' * 101},
      {'conflict_id': 'ru_ua'},
      {'conflict_id': original[1]['conflict_id']},
      {'color': '#12345Z'},
      {'flag': 'IN PK'},
      {'latitude': '90.000001'},
      {'longitude': '-180.000001'},
      {'latitude': 'NaN'},
      {'longitude': '12.1234567'},
      {'display_order': '1'},
    ]
    for updates in changes:
      with self.subTest(updates=updates):
        rows = copy.deepcopy(original)
        rows[0].update(updates)
        with self.assertRaises(ValueError):
          validate_table(rows)


if __name__ == '__main__':
  unittest.main()
