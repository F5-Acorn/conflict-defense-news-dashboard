'''엑셀 기준 테이블과 DB 유형값의 화면 표시 이름.'''

KIND_LABELS = {'wp': '무기', 'tech': '기술'}


def load_reference_tables():
  '''엑셀에서 분쟁·범주·사전·사용 표현의 5개 테이블을 읽는다.'''
  from data.excel_loader import load_tables

  return {
    name: frame
    for name, frame in load_tables().items()
    if name not in ('articles', 'result')
  }
