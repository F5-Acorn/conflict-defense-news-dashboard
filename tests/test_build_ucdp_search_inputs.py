'''분쟁별 전체 기간 조회, 날짜 경계, 사건 없는 분쟁, 국가코드·해시를 검사한다.'''

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_ucdp_search_inputs import (
  DEFAULT_COUNTRY_CODES,
  OUTPUT_FILES,
  build_search_inputs,
)
from scripts.prepare_ucdp import METADATA_NAME, OUTPUT_NAME
from tests.ucdp_fixtures import Inputs, acd_row, event, write_csv


class BuildUcdpSearchInputsTest(unittest.TestCase):
  def setUp(self):
    temp = TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    self.inputs = Inputs(Path(temp.name))
    self.inputs.run()
    self.output = self.inputs.root / 'search'

  def build(self, mapping=DEFAULT_COUNTRY_CODES):
    return build_search_inputs(
      self.inputs.output / METADATA_NAME, self.inputs.actors, mapping, self.output
    )

  def rows(self, name):
    with (self.output / name).open(encoding='utf-8-sig') as file:
      return list(csv.DictReader(file))

  def test_full_period_is_one_batch_and_clips_to_as_of(self):
    plan = self.build()
    self.assertEqual(plan['counts']['batches'], 1)
    self.assertEqual(len(plan['batches']), 1)
    batch = plan['batches'][0]
    self.assertEqual(batch['batch_id'], 'ucdp_10_20251215_20260215')
    self.assertEqual(batch['shared_period_query_id'], '20251215_20260215')
    self.assertEqual(batch['ucdp_hint_event_count'], 1)
    self.assertEqual(batch['article_published_start'], '2025-12-15')
    self.assertEqual(batch['article_published_end_exclusive'], '2026-02-16')
    self.assertEqual(batch['mention_start'], '2025-12-15')
    self.assertEqual(batch['mention_end_exclusive'], '2026-02-16')
    self.assertEqual(batch['event_partition_start'], '2015-02-19')
    self.assertEqual(batch['event_partition_end_exclusive'], '2026-02-16')
    self.assertFalse(batch['ucdp_event_match_required'])
    self.assertEqual(batch['candidate_match_mode'], 'geography_or_actor')

  def test_requested_dates_stay_exact_and_mentions_include_delay(self):
    for start, end, end_exclusive, mention_end in [
      ('2025-12-15', '2026-01-03', '2026-01-04', '2026-01-18'),
      ('2025-12-20', '2025-12-20', '2025-12-21', '2026-01-04'),
    ]:
      with self.subTest(start=start, end=end):
        self.inputs.scope.update(analysis_start=start, analysis_end=end)
        self.inputs.save_scope()
        self.inputs.run()
        plan = self.build()
        self.assertEqual(len(plan['batches']), 1)
        batch = plan['batches'][0]
        self.assertEqual(batch['article_published_start'], start)
        self.assertEqual(batch['article_published_end_exclusive'], end_exclusive)
        self.assertEqual(batch['mention_start'], start)
        self.assertEqual(batch['mention_end_exclusive'], mention_end)
        self.assertEqual(batch['ucdp_hint_event_count'], 1)

  def test_each_conflict_has_one_full_period_batch(self):
    self.inputs.write_acd(
      [acd_row(), acd_row(conflict_id='20', side_b_id='4', gwno_b='2')]
    )
    self.inputs.run()
    plan = self.build()
    self.assertEqual(plan['counts']['batches'], 2)
    self.assertEqual(len(plan['batches']), 2)
    batches = {row['candidate_conflict_id']: row for row in plan['batches']}
    self.assertEqual(set(batches), {'ucdp_10', 'ucdp_20'})
    self.assertEqual(len({row['batch_id'] for row in batches.values()}), 2)
    for batch in batches.values():
      self.assertEqual(batch['article_published_start'], '2025-12-15')
      self.assertEqual(batch['article_published_end_exclusive'], '2026-02-16')
      self.assertEqual(batch['shared_period_query_id'], '20251215_20260215')
    self.assertEqual(batches['ucdp_10']['ucdp_hint_event_count'], 1)
    self.assertEqual(batches['ucdp_20']['ucdp_hint_event_count'], 0)

  def test_zero_event_target_has_aliases_participants_and_batches(self):
    x = self.inputs
    x.write_events([])
    x.run()
    plan = self.build()
    self.assertEqual(plan['counts']['events'], 0)
    self.assertEqual(len(plan['batches']), 1)
    self.assertEqual(plan['batches'][0]['gdelt_geo_country_codes'], ['RS', 'UP'])
    self.assertIn('government of alpha', plan['batches'][0]['actor_terms'])
    self.assertEqual(self.rows('event_match_hints.csv'), [])

  def test_hints_are_optional_and_aliases_preserve_original_names(self):
    self.build()
    hints = self.rows('event_match_hints.csv')
    self.assertEqual(hints[0]['hint_radius_km'], '25')
    self.assertEqual(hints[0]['required_for_article_inclusion'], 'False')
    aliases = {(r['actor_id'], r['alias']): r for r in self.rows('actor_aliases.csv')}
    self.assertIn(('2', 'Groupe café, original'), aliases)
    self.assertNotIn(('2', 'original'), aliases)
    self.assertIn(('2', 'Beta'), aliases)
    self.assertEqual(aliases[('2', 'B')]['needs_review'], 'True')

  def test_coalition_and_occurrence_countries_are_not_conflated(self):
    x = self.inputs
    x.write_acd([acd_row(side_a_id='1, 4', gwno_a='365, 2')])
    x.write_events([event(country_id='666', country='Israel')])
    x.run()
    self.build()
    conflict = self.rows('conflicts.csv')[0]
    self.assertEqual(conflict['participant_country_ids'], '2|365|369')
    self.assertEqual(conflict['observed_country_ids'], '666')
    self.assertEqual(
      set(conflict['gdelt_geo_country_codes'].split('|')),
      {'US', 'RS', 'UP', 'GZ', 'IS', 'WE'},
    )

  def test_changed_events_or_actors_preserve_existing_outputs(self):
    self.build()
    before = {name: (self.output / name).read_bytes() for name in OUTPUT_FILES}
    path = self.inputs.output / OUTPUT_NAME
    path.write_bytes(path.read_bytes() + b'\n')
    with self.assertRaisesRegex(ValueError, 'SHA-256'):
      self.build()
    self.assertEqual(
      before, {name: (self.output / name).read_bytes() for name in OUTPUT_FILES}
    )
    self.inputs.run()
    self.inputs.actors.write_bytes(self.inputs.actors.read_bytes() + b'\n')
    with self.assertRaisesRegex(ValueError, 'Actor SHA-256'):
      self.build()

  def test_missing_participant_country_mapping_fails_even_without_events(self):
    self.inputs.write_events([])
    self.inputs.run()
    path = self.inputs.root / 'mapping.csv'
    write_csv(
      path,
      ['ucdp_country_id', 'ucdp_country_name', 'gdelt_geo_country_code'],
      [
        {
          'ucdp_country_id': '369',
          'ucdp_country_name': 'Ukraine',
          'gdelt_geo_country_code': 'UP',
        }
      ],
    )
    with self.assertRaisesRegex(ValueError, '365'):
      self.build(path)
    self.assertFalse(self.output.exists())


if __name__ == '__main__':
  unittest.main()
