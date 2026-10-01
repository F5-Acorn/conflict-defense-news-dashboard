'''범주별 기사 수를 한글 워드클라우드로 표시한다. 아래 상수로 스타일을 조정한다.'''

import hashlib
from base64 import b64encode
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
import streamlit as st
import streamlit.components.v2 as components
from PIL import ImageColor
from wordcloud import WordCloud

from config import CHART_BACKGROUND
from ui.loading import loading_html

# 이 설정을 수정하고 앱을 새로고침하면 바뀐 설정으로 이미지를 다시 생성한다.
WORDCLOUD_STYLE = {
  'font_path': str(
    Path(__file__).resolve().parents[1] / 'assets/fonts/Pretendard-Bold.ttf'
  ),
  'width': 700,
  'height': 500,
  'prefer_horizontal': 0.65,
  'background_color': CHART_BACKGROUND,
  'max_words': 200,
  'max_font_size': None,
  'min_font_size': 12,
  'relative_scaling': 0.5,
  'random_state': 42,
  'repeat': False,
  'margin': 0,
}
# 원하는 HEX 색상 튜플로 바꾸면 워드클라우드의 글자색만 변경된다.
WORDCLOUD_COLORS = ('#bae6fd', '#7dd3fc', '#38bdf8', '#0ea5e9')
# 정확한 기사 수는 유지하고, 이미지의 글자 크기와 상위 범주 강조만 조정한다.
WORDCLOUD_EMPHASIS = {'weight_power': 0.5, 'top_count': 3, 'top_color': '#e0f2fe'}
# 같은 단어를 반복하지 않고, 여러 배치 중 단어 누락이 적고 촘촘한 결과를 고른다.
WORDCLOUD_LAYOUT_ATTEMPTS = 3

wordcloud_component = components.component(
  'responsive_wordcloud',
  html=f'''<div class="period-wordcloud-image">
            {loading_html("워드클라우드를 준비하는 중…")}
            <img alt="무기·기술 워드클라우드" style="visibility:hidden" />
          </div>''',
  js=(Path(__file__).with_name('frontend') / 'wordcloud.js').read_text(
    encoding='utf-8'
  ),
  isolate_styles=False,
)


def _style_for_size(size):
  style = WORDCLOUD_STYLE.copy()
  if isinstance(size, dict) and all(
    isinstance(size.get(axis), int)
    and not isinstance(size[axis], bool)
    and 32 <= size[axis] <= 2048
    for axis in ('width', 'height')
  ):
    style.update(width=size['width'], height=size['height'])
  return style


@st.fragment
def render_wordcloud_panel(frequencies, *, images, key):
  if not frequencies or not any(count > 0 for count in frequencies.values()):
    st.info('선택한 조건에서 사용이 확인된 범주가 없습니다.')
    return
  size = st.session_state.get(key, {}).get('size')
  style = _style_for_size(size)
  # 최초 진입은 크기만 측정하고, 실제 부모 크기를 받은 뒤 이미지를 생성한다.
  content = (
    wordcloud_image(frequencies, images=images, size=size) if size is not None else None
  )
  wordcloud_component(
    data={
      'image': f'data:image/png;base64,{b64encode(content).decode()}'
      if content is not None
      else None,
      'size': {'width': style['width'], 'height': style['height']},
    },
    key=key,
    height='stretch',
    on_size_change=lambda: None,
  )


def wordcloud_image(frequencies, *, images=None, size=None):
  if not frequencies or not any(count > 0 for count in frequencies.values()):
    return None
  key = wordcloud_key(frequencies, size=size)
  if images is not None and key in images:
    return images[key]
  return _render_wordcloud(
    frequencies,
    _style_for_size(size),
    WORDCLOUD_COLORS,
    key[1],
    WORDCLOUD_EMPHASIS,
    WORDCLOUD_LAYOUT_ATTEMPTS,
  )


def wordcloud_key(frequencies, *, size=None):
  '''사전 준비 이미지에도 현재 글꼴과 스타일의 동일한 캐시 기준을 적용한다.'''
  # 같은 경로의 TTF가 교체된 경우에도 새 글꼴로 이미지를 생성한다.
  path = Path(WORDCLOUD_STYLE['font_path'])
  stat = path.stat()
  font_hash = _font_hash(str(path), stat.st_mtime_ns, stat.st_size)
  return (
    tuple(sorted(frequencies.items())),
    font_hash,
    tuple(sorted(_style_for_size(size).items())),
    WORDCLOUD_COLORS,
    tuple(sorted(WORDCLOUD_EMPHASIS.items())),
    WORDCLOUD_LAYOUT_ATTEMPTS,
  )


@lru_cache(maxsize=4)
def _font_hash(path, modified, size):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@st.cache_data(show_spinner=False, max_entries=128)
def _render_wordcloud(frequencies, style, colors, font_hash, emphasis, attempts):
  return render_wordcloud(
    frequencies, style, colors, emphasis=emphasis, attempts=attempts
  )


def render_wordcloud(
  frequencies, style, colors, *, emphasis=None, attempts=WORDCLOUD_LAYOUT_ATTEMPTS
):
  emphasis = WORDCLOUD_EMPHASIS if emphasis is None else emphasis
  ordered = sorted(
    ((word, count) for word, count in frequencies.items() if count > 0),
    key=lambda item: (-item[1], item[0]),
  )
  top = {word for word, _ in ordered[: emphasis['top_count']]}
  weights = {word: count ** emphasis['weight_power'] for word, count in ordered}

  def color_for(word, **kwargs):
    if word in top:
      return emphasis['top_color']
    index = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16)
    return colors[index % len(colors)]

  background = np.array(ImageColor.getrgb(style['background_color']))
  canvas, best_score = None, (-1, -1, -1)
  for attempt in range(attempts):
    candidate_style = dict(style, random_state=style['random_state'] + attempt)
    cloud = WordCloud(
      **candidate_style, color_func=color_for
    ).generate_from_frequencies(weights)
    candidate = cloud.to_image()
    rotated = any(word[3] is not None for word in cloud.layout_)
    ink = int(np.any(np.asarray(candidate) != background, axis=2).sum())
    score = (len(cloud.layout_), int(rotated), ink)
    if score > best_score:
      canvas, best_score = candidate, score
  output = BytesIO()
  canvas.save(output, format='PNG')
  return output.getvalue()
