'''운영체제 글꼴에 의존하지 않고 국기 이모지를 로컬 SVG로 표시한다.'''

import base64
import re
from functools import lru_cache
from html import escape
from pathlib import Path

FLAG_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'flags'
COUNTRY_NAMES = {
  'AF': '아프가니스탄',
  'BD': '방글라데시',
  'CD': '콩고민주공화국',
  'CN': '중국',
  'ER': '에리트레아',
  'ET': '에티오피아',
  'GB': '영국',
  'IL': '이스라엘',
  'IN': '인도',
  'IQ': '이라크',
  'IR': '이란',
  'KG': '키르기스스탄',
  'KH': '캄보디아',
  'MM': '미얀마',
  'PK': '파키스탄',
  'RU': '러시아',
  'RW': '르완다',
  'SY': '시리아',
  'TH': '태국',
  'TJ': '타지키스탄',
  'UA': '우크라이나',
  'US': '미국',
  'YE': '예멘',
}


@lru_cache(maxsize=256)
def _flag_uri(code):
  try:
    content = (FLAG_DIR / f'{code.lower()}.svg').read_bytes()
  except OSError:
    return None
  return 'data:image/svg+xml;base64,' + base64.b64encode(content).decode('ascii')


def render_flags(value):
  '''지역 표시 문자 두 개를 국가 코드로 바꾸며, 원본의 국가 순서를 보존한다.'''
  icons = []
  for pair in re.findall(r'[\U0001f1e6-\U0001f1ff]{2}', value or ''):
    code = ''.join(chr(ord(char) - 0x1F1E6 + ord('A')) for char in pair)
    label = escape(f'{COUNTRY_NAMES.get(code, code)} 국기', quote=True)
    uri = _flag_uri(code)
    if uri:
      icons.append(
        f'<img class="conflict-flag" src="{uri}" alt="{label}" '
        f'title="{label}" width="20" height="20" draggable="false">'
      )
    else:
      icons.append(
        f'<span class="conflict-flag-fallback" title="{label}">{code}</span>'
      )
  return f'<span class="conflict-flags">{"".join(icons)}</span>' if icons else ''
