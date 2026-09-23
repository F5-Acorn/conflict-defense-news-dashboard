'''엑셀 원본과 화면 집계의 공통 스냅샷. 실행 중 데이터를 생성하지 않는다.'''

import streamlit as st

from config import build_settings
from data.excel_loader import file_payloads, load_tables, read_tables
from services.analysis_service import build_dashboard_data


@st.cache_data(show_spinner=False, max_entries=4)
def _build_snapshot(payloads):
  tables = read_tables(payloads)
  articles, categories = build_dashboard_data(tables)
  return {
    'tables': tables,
    'settings': build_settings(tables),
    'article_daily': articles,
    'category_daily': categories,
  }


def load_dashboard_snapshot(directory=None):
  '''설정과 집계에 동일한 파일 내용을 사용하며 모든 파일 변경을 캐시에 반영한다.'''
  return _build_snapshot(file_payloads(directory))


def load_sample_tables():
  '''기존 호출부 호환용. 저장된 엑셀 7개 테이블을 반환한다.'''
  return load_tables()


def load_dashboard_data():
  '''화면용 (일별 기사 지표, 범주별 사용 보도 수) 반환 형식을 유지한다.'''
  snapshot = load_dashboard_snapshot()
  return snapshot['article_daily'], snapshot['category_daily']
