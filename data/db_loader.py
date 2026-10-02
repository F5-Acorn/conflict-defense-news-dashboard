'''dashboarddb_dev_v1의 데이터를 읽어 화면 내부 규격으로 변환한다.'''

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from data.table_contract import COLUMNS, DataValidationError, validate_tables

DB_KINDS = {'wp': 'wp', 'tech': 'tech', 'weapon': 'wp', 'technology': 'tech'}


# secrets.toml 파일에서 DB url 정보를 조회해서 반환하는 함수
def database_url():
  try:
    url = st.secrets['connections']['dashboarddb']['url']
    if not isinstance(url, str) or not url.startswith('mysql+pymysql://'):
      raise ValueError
    return url
  except (KeyError, FileNotFoundError, ValueError) as exc:
    raise DataValidationError(
      '.streamlit/secrets.toml의 [connections.dashboarddb] url을 확인해주세요.'
    ) from exc


@st.cache_resource(show_spinner=False, max_entries=2)
def get_db_engine(url):
  '''URL별 DB 엔진을 생성·재사용하는 함수로, 캐싱 데이터 생성 시점이 30분 이내라면 재사용, 아니면 생성한다.'''
  try:
    return create_engine(
      url,
      pool_pre_ping=True,
      pool_recycle=1800,
      isolation_level='REPEATABLE READ',
      connect_args={'connect_timeout': 10, 'read_timeout': 60, 'write_timeout': 10},
    )
  except (SQLAlchemyError, ValueError) as exc:
    raise DataValidationError(
      'DB 엔진을 생성할 수 없습니다. 연결 URL과 엔진 설정을 확인해주세요.'
    ) from exc


def normalize_tables(tables):
  categories = tables['categories']
  categories['kind'] = categories['kind'].replace(DB_KINDS)
  validate_tables(tables)
  return tables


def read_tables_from_db(url, *, engine=None):
  '''하나의 읽기 전용 트랜잭션에서 여섯 테이블의 일관된 데이터를 조회한다.'''
  tables = {}
  name = None
  try:
    with (engine if engine is not None else get_db_engine(url)).connect() as connection:
      connection.exec_driver_sql(
        'START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY'
      )
      for name, columns in COLUMNS.items():
        fields = ', '.join(f'`{column}`' for column in columns)
        order = ', '.join(
          f'`{column}`' for column in (columns[:2] if name == 'result' else columns[:1])
        )
        if name == 'conflicts':
          order = "CAST(SUBSTRING_INDEX(conflict_id, '_', -1) AS UNSIGNED), conflict_id"
        tables[name] = pd.read_sql_query(
          text(f'SELECT {fields} FROM `{name}` ORDER BY {order}'),
          connection,
          coerce_float=False,
        )
  except SQLAlchemyError as exc:
    source = f'[{name} 테이블] ' if name else ''
    # 드라이버 예외의 URL·계정·SQL 원문을 화면에 노출하지 않는다.
    raise DataValidationError(
      f'{source}DB를 조회할 수 없습니다. 연결 설정·접속 권한·테이블을 확인해주세요.'
    ) from exc
  return normalize_tables(tables)
