'''DB 데이터·설정·집계를 동일한 스냅샷으로 캐시한다.'''

import hashlib

import pandas as pd
import streamlit as st

from config import build_settings
from data.db_loader import database_url, read_tables_from_db
from services.analysis_service import build_dashboard_data
from services.detail_service import build_reports


def dataset_revision(tables):
  revision = hashlib.sha256()
  for name, frame in tables.items():
    revision.update(name.encode())
    revision.update(pd.util.hash_pandas_object(frame, index=False).values.tobytes())
  return revision.hexdigest()


@st.cache_data(show_spinner=False, ttl=60, max_entries=2)
def _build_snapshot(url):
  tables = read_tables_from_db(url)
  reports = build_reports(tables)
  articles, categories = build_dashboard_data(tables, reports)
  return {
    'tables': tables,
    'revision': dataset_revision(tables),
    'reports': reports,
    'settings': build_settings(tables),
    'article_daily': articles,
    'category_daily': categories,
  }


def load_dashboard_snapshot():
  '''60초 경과 후 다음 앱 실행에서 DB와 집계를 함께 갱신한다.'''
  return _build_snapshot(database_url())
