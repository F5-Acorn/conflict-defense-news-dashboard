'''국가 간 분쟁 선별, 잠정 자료 갱신, 출처 보존과 실패 처리를 검사한다.'''

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.prepare_ucdp import METADATA_NAME, OUTPUT_NAME, REVIEW_NAME, sha256_file
from tests.ucdp_fixtures import Inputs, acd_row, event


class PrepareUcdpTest(unittest.TestCase):
  def setUp(self):
    temp = TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    self.inputs = Inputs(Path(temp.name))

  def test_only_interstate_parties_pass_and_original_values_survive(self):
    x = self.inputs
    x.write_acd(
      [acd_row(), acd_row(conflict_id='20', type_of_conflict='3', side_b_id='3')]
    )
    x.write_events(
      [
        event(),
        event('2', conflict_new_id='20', side_b_new_id='3'),
        event('3', type_of_violence='2'),
        event('4', type_of_violence='3'),
        event('5', side_b_new_id='4'),
        event('6', side_a_new_id='2', side_b_new_id='1'),
        event('7', date_start='2025-12-01', date_end='2025-12-01'),
      ]
    )
    original = sha256_file(x.ged)
    result = x.run(chunksize=2)
    rows = x.read(OUTPUT_NAME)
    self.assertEqual([r['id'] for r in rows], ['1', '6'])
    self.assertEqual(rows[0]['latitude'], '50.450000')
    self.assertEqual(rows[0]['date_start'], '2025-12-20 00:00:00.000')
    self.assertEqual(rows[0]['classification_status'], 'interstate_confirmed')
    self.assertEqual(sha256_file(x.ged), original)
    self.assertEqual(
      x.read(REVIEW_NAME)[0]['classification_reason'], 'acd_party_mismatch'
    )
    self.assertEqual(result['output_rows'], 2)

  def test_missing_annual_year_retains_event_but_explicit_intrastate_excludes(self):
    x = self.inputs
    x.write_acd([acd_row(year='2024')])
    x.write_events([event(active_year='0')])
    x.run()
    self.assertEqual(
      x.read(OUTPUT_NAME)[0]['classification_status'], 'interstate_reference'
    )
    self.assertEqual(x.read(OUTPUT_NAME)[0]['needs_review'], 'True')
    x.write_acd([acd_row(year='2024'), acd_row(type_of_conflict='4')])
    x.run()
    self.assertEqual(x.read(OUTPUT_NAME), [])

  def test_candidate_latest_revision_and_new_government_pair_are_provisional(self):
    x = self.inputs
    january = event('100', year='2026', date_start='2026-01-31', date_end='2026-02-02')
    x.add_candidate('jan.csv', [january])
    x.add_candidate(
      'feb.csv',
      [
        {**january, 'adm_1': 'Revised location'},
        event(
          '101',
          year='2026',
          conflict_new_id='99',
          side_b_new_id='4',
          date_start='2026-02-01',
          date_end='2026-02-01',
        ),
        event(
          '102',
          year='2026',
          conflict_new_id='98',
          side_b_new_id='999',
          date_start='2026-02-01',
          date_end='2026-02-01',
        ),
      ],
      start='2026-02-01',
      end='2026-02-28',
    )
    result = x.run()
    rows = {r['id']: r for r in x.read(OUTPUT_NAME)}
    self.assertEqual(rows['100']['adm_1'], 'Revised location')
    self.assertEqual(rows['100']['source_version'], 'feb.csv')
    self.assertEqual(rows['101']['classification_status'], 'state_pair_candidate')
    self.assertEqual(rows['101']['needs_review'], 'True')
    self.assertEqual(result['candidate_duplicate_rows_replaced'], 1)
    self.assertEqual(x.read(REVIEW_NAME)[0]['id'], '102')
    self.assertEqual(result['analysis_end'], '2026-02-15')
    self.assertEqual(result['scope']['analysis_end'], '2026-12-31')

  def test_revised_violence_type_removes_previously_selected_candidate(self):
    x = self.inputs
    row = event('100', year='2026', date_start='2026-01-31', date_end='2026-02-02')
    x.add_candidate('jan.csv', [row])
    x.add_candidate(
      'feb.csv', [{**row, 'type_of_violence': '3'}], '2026-02-01', '2026-02-28'
    )
    x.run()
    self.assertNotIn('100', {r['id'] for r in x.read(OUTPUT_NAME)})

  def test_empty_ged_still_keeps_annual_interstate_target(self):
    x = self.inputs
    x.write_events([])
    result = x.run()
    self.assertEqual(result['output_rows'], 0)
    self.assertEqual(result['targets'][0]['ucdp_conflict_id'], '10')
    self.assertEqual(x.read(OUTPUT_NAME), [])

  def test_duplicate_acd_or_missing_candidate_fails_without_overwriting(self):
    x = self.inputs
    x.run()
    before = {p.name: p.read_bytes() for p in x.output.iterdir()}
    x.write_acd([acd_row(), acd_row()])
    with self.assertRaisesRegex(ValueError, '중복'):
      x.run()
    self.assertEqual(before, {p.name: p.read_bytes() for p in x.output.iterdir()})
    x.write_acd([acd_row()])
    x.add_candidate('missing.csv', [])
    (x.root / 'missing.csv').unlink()
    with self.assertRaises(FileNotFoundError):
      x.run()
    self.assertEqual(before, {p.name: p.read_bytes() for p in x.output.iterdir()})

  def test_invalid_date_or_duplicate_ged_does_not_replace_results(self):
    x = self.inputs
    x.run()
    before = (x.output / METADATA_NAME).read_bytes()
    x.write_events([event(), event()])
    with self.assertRaisesRegex(ValueError, '중복'):
      x.run(chunksize=1)
    self.assertEqual(before, (x.output / METADATA_NAME).read_bytes())
    x.write_events([event(date_end='2025-12-19')])
    with self.assertRaisesRegex(ValueError, '시작일'):
      x.run()
    self.assertEqual(before, (x.output / METADATA_NAME).read_bytes())

  def test_metadata_hashes_and_candidate_status_are_recorded(self):
    x = self.inputs
    result = x.run()
    self.assertEqual(json.loads((x.output / METADATA_NAME).read_text()), result)
    self.assertEqual(result['output_sha256'], sha256_file(x.output / OUTPUT_NAME))
    self.assertEqual(result['references']['acd']['sha256'], sha256_file(x.acd))
    self.assertEqual(result['annual_coverage_end'], '2025-12-31')
    self.assertIsNone(result['download_date'])


if __name__ == '__main__':
  unittest.main()
