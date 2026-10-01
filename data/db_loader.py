'''dashboarddb_dev_v1의 데이터를 읽어 화면 내부 규격으로 변환한다.'''

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from data.constants import UsageCode
from data.table_contract import COLUMNS, DataValidationError, _integers, validate_tables

# DB 판정 정의: 0=비사용, 1=사용, 2=불확실. 값으로 자동 추측하지 않는다.
DB_USAGE_CODES = {0: UsageCode.NOT_USED, 1: UsageCode.USED, 2: UsageCode.UNCERTAIN}
DB_KINDS = {'wp': 'wp', 'tech': 'tech', 'weapon': 'wp', 'technology': 'tech'}


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
  try:
    return create_engine(
      url,
      pool_pre_ping=True,
      pool_recycle=1800,
      isolation_level='REPEATABLE READ',
      connect_args={'connect_timeout': 10, 'read_timeout': 60, 'write_timeout': 10},
    )
  except (SQLAlchemyError, ValueError) as exc:
    raise DataValidationError('DB 연결 URL 형식을 확인해주세요.') from exc


def normalize_tables(tables):
  results = tables['result']
  codes = _integers('result', 'usage_code', results['usage_code'], 0, 2)
  results['usage_code'] = codes.map(DB_USAGE_CODES).astype('int64')
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
