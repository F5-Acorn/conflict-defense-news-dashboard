'''공통 집계를 최초 준비하고 1시간마다 백그라운드에서 원자적으로 갱신한다.'''

import hashlib
import logging
from collections import OrderedDict
from threading import Event, Lock, Thread
from time import perf_counter

import pandas as pd
import streamlit as st

from config import build_settings
from data.constants import KIND_LABELS
from data.db_loader import database_url, get_db_engine, read_tables_from_db
from services.analysis_service import (
  STATUS_COLUMNS,
  build_dashboard_data,
  build_overview_article_counts,
  build_status_daily,
  category_summary,
  ranked_categories,
  summary_trend,
  summary_word_counts,
)
from services.detail_service import (
  build_reports,
  classification_csv,
  classification_details,
)

REFRESH_SECONDS = 3600


class ViewCache:
  '''한 스냅샷의 작은 화면 결과만 제한된 수로 재사용한다.'''

  def __init__(self, limit=128):
    self.limit = limit
    self._lock = Lock()
    self._items = OrderedDict()

  def get(self, key, build):
    with self._lock:
      if key in self._items:
        self._items.move_to_end(key)
        return self._items[key]
    value = build()
    with self._lock:
      self._items[key] = value
      self._items.move_to_end(key)
      while len(self._items) > self.limit:
        self._items.popitem(last=False)
    return value

  def __getstate__(self):
    return {'limit': self.limit, '_items': self._items}

  def __setstate__(self, state):
    self.__dict__.update(state)
    self._lock = Lock()


def dataset_revision(tables):
  revision = hashlib.sha256()
  for name, frame in tables.items():
    revision.update(name.encode())
    revision.update(pd.util.hash_pandas_object(frame, index=False).values.tobytes())
  return revision.hexdigest()


def _snapshot_from_tables(tables, revision):
  started = perf_counter()
  reports = build_reports(tables)
  articles, categories = build_dashboard_data(tables, reports)
  settings = build_settings(tables)
  daily = build_status_daily(reports)
  monthly = (
    daily.assign(date=daily['date'].dt.to_period('M').dt.to_timestamp())
    .groupby(
      ['date', 'conflict_id', 'conflict', 'category_id', 'kind', 'category'],
      as_index=False,
      observed=True,
    )[[*STATUS_COLUMNS.values(), 'total_count']]
    .sum()
  )
  meta = tables['categories'].rename(columns={'category_name': 'category'}).copy()
  meta['kind'] = meta['kind'].map(KIND_LABELS)
  overview, usage_articles_total = build_overview_article_counts(tables)
  rankings = {
    conflict: {
      kind: ranked_categories(
        categories.loc[
          categories['conflict'].eq(conflict) & categories['kind'].eq(kind)
        ]
      )
      for kind in KIND_LABELS.values()
    }
    for conflict in settings['conflicts']
  }
  details = {
    kind: classification_details(tables, kind) for kind in KIND_LABELS.values()
  }
  snapshot = {
    'tables': tables,
    'revision': revision,
    'reports': reports,
    'settings': settings,
    'article_daily': articles,
    'category_daily': categories,
    'category_status_daily': daily,
    'category_status_monthly': monthly,
    'category_meta': meta,
    'overview_summary': {
      'articles': overview,
      'usage_articles_total': usage_articles_total,
      'rankings': rankings,
    },
    'classification_details': details,
    'classification_csv': {
      kind: classification_csv(tables, kind, details=details[kind])
      for kind in KIND_LABELS.values()
    },
    'view_cache': ViewCache(),
    'wordcloud_images': {},
    'timings': {},
  }
  snapshot['timings']['prepare_seconds'] = perf_counter() - started
  _warm_defaults(snapshot)
  return snapshot


def _warm_defaults(snapshot):
  if snapshot['settings']['start'] is None:
    return
  # 순수 이미지 생성 함수만 사용한다. 백그라운드에서 Streamlit UI를 호출하지 않는다.
  from ui.wordcloud_view import (
    WORDCLOUD_COLORS,
    WORDCLOUD_ELLIPSE,
    WORDCLOUD_STYLE,
    render_wordcloud,
    wordcloud_key,
  )
  from utils.state import default_filters

  started = perf_counter()
  for page in ('annual', 'monthly', 'weekly'):
    filters = default_filters(snapshot['settings'], page)
    start, end = filters['period']
    kind = filters['kind']
    summary = category_summary(snapshot, '전체', start, end, kind)
    selected = summary['category_id'].head(3).tolist()
    summary_trend(
      snapshot,
      '전체',
      start,
      end,
      kind,
      selected,
      'day' if page in ('monthly', 'weekly') else 'month',
    )
    frequencies = summary_word_counts(summary)
    key = wordcloud_key(frequencies) if frequencies else None
    if key is not None and key not in snapshot['wordcloud_images']:
      snapshot['wordcloud_images'][key] = render_wordcloud(
        frequencies,
        WORDCLOUD_STYLE,
        WORDCLOUD_COLORS,
        WORDCLOUD_ELLIPSE,
      )
  snapshot['timings']['warm_seconds'] = perf_counter() - started


class SnapshotStore:
  def __init__(self, loader, *, refresh_seconds=REFRESH_SECONDS, start_worker=True):
    self._loader = loader
    self._lock = Lock()
    self._refresh_lock = Lock()
    self._stop = Event()
    self._refresh_seconds = refresh_seconds
    self._snapshot = self._load(None)
    self._thread = None
    if start_worker:
      self._thread = Thread(target=self._run, name='dashboard-snapshot', daemon=True)
      self._thread.start()

  def _load(self, previous):
    started = perf_counter()
    tables = self._loader()
    read_seconds = perf_counter() - started
    revision = dataset_revision(tables)
    if previous is not None and previous['revision'] == revision:
      return previous
    snapshot = _snapshot_from_tables(tables, revision)
    snapshot['timings']['read_seconds'] = read_seconds
    snapshot['timings']['total_seconds'] = perf_counter() - started
    return snapshot

  def current(self):
    with self._lock:
      return self._snapshot

  def refresh(self):
    if not self._refresh_lock.acquire(blocking=False):
      return False
    try:
      new = self._load(self.current())
      if not self._stop.is_set():
        with self._lock:
          self._snapshot = new
      return True
    except Exception:
      logging.getLogger(__name__).warning(
        '백그라운드 데이터 갱신 실패: 이전 정상 스냅샷을 유지합니다.'
      )
      return False
    finally:
      self._refresh_lock.release()

  def _run(self):
    while not self._stop.wait(self._refresh_seconds):
      self.refresh()

  def close(self):
    self._stop.set()


@st.cache_resource(
  show_spinner=False, max_entries=1, on_release=lambda store: store.close()
)
def get_snapshot_store(url):
  engine = get_db_engine(url)
  return SnapshotStore(lambda: read_tables_from_db(url, engine=engine))


def load_dashboard_snapshot():
  '''완성된 공유 스냅샷만 반환한다. 화면 조작에서는 DB와 전체 정제를 실행하지 않는다.'''
  return get_snapshot_store(database_url()).current()
