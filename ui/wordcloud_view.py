'''범주별 기사 수를 한글 워드클라우드로 표시한다. 아래 상수로 스타일을 조정한다.'''

import hashlib
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageChops
from wordcloud import WordCloud

from config import CATEGORY_PALETTE, CHART_BACKGROUND

# 이 설정을 수정하고 앱을 새로고침하면 바뀐 설정으로 이미지를 다시 생성한다.
WORDCLOUD_STYLE = {
  'font_path': str(Path(__file__).resolve().parents[1] / 'assets/fonts/Pretendard.ttf'),
  'width': 700,
  'height': 1100,
  'prefer_horizontal': 1.0,
  'background_color': CHART_BACKGROUND,
  'max_words': 200,
  'max_font_size': 160,
  'min_font_size': 18,
  'relative_scaling': 0.5,
  'random_state': 42,
  'repeat': False,
  'margin': 0,
}
# 캔버스 대비 중앙 타원의 가로·세로 비율. 글자 배치 영역만 제한한다.
WORDCLOUD_ELLIPSE = {'width_ratio': 0.8, 'height_ratio': 0.8}
# 원하는 HEX 색상 튜플로 바꾸면 워드클라우드의 글자색만 변경된다.
WORDCLOUD_COLORS = CATEGORY_PALETTE


def wordcloud_image(frequencies, *, images=None):
  if not frequencies:
    return None
  key = wordcloud_key(frequencies)
  if images is not None and key in images:
    return images[key]
  return _render_wordcloud(
    frequencies,
    WORDCLOUD_STYLE,
    WORDCLOUD_COLORS,
    WORDCLOUD_ELLIPSE,
    key[1],
  )


def wordcloud_key(frequencies):
  '''사전 준비 이미지에도 현재 글꼴과 스타일의 동일한 캐시 기준을 적용한다.'''
  # 같은 경로의 TTF가 교체된 경우에도 새 글꼴로 이미지를 생성한다.
  path = Path(WORDCLOUD_STYLE['font_path'])
  stat = path.stat()
  font_hash = _font_hash(str(path), stat.st_mtime_ns, stat.st_size)
  return (
    tuple(sorted(frequencies.items())),
    font_hash,
    tuple(sorted(WORDCLOUD_STYLE.items())),
    WORDCLOUD_COLORS,
    tuple(sorted(WORDCLOUD_ELLIPSE.items())),
  )


@lru_cache(maxsize=4)
def _font_hash(path, modified, size):
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@st.cache_data(show_spinner=False, max_entries=128)
def _render_wordcloud(frequencies, style, colors, ellipse, font_hash):
  return render_wordcloud(frequencies, style, colors, ellipse)


def render_wordcloud(frequencies, style, colors, ellipse):
  width, height = style['width'], style['height']
  y, x = np.ogrid[:height, :width]
  inside = ((x - (width - 1) / 2) / (width * ellipse['width_ratio'] / 2)) ** 2 + (
    (y - (height - 1) / 2) / (height * ellipse['height_ratio'] / 2)
  ) ** 2 <= 1
  # WordCloud에서 흰색(255)은 글자를 배치하지 않는 영역이다.
  mask = np.where(inside, 0, 255).astype('uint8')
  cloud = WordCloud(
    **style,
    mask=mask,
    color_func=lambda word, **kwargs: colors[sum(map(ord, word)) % len(colors)],
  ).generate_from_frequencies(frequencies)
  rendered = cloud.to_image()
  canvas = Image.new(rendered.mode, rendered.size, style['background_color'])
  bounds = ImageChops.difference(rendered, canvas).getbbox()
  if bounds:
    words = rendered.crop(bounds)
    canvas = Image.new(
      rendered.mode, (words.width + 16, words.height + 16), style['background_color']
    )
    canvas.paste(words, (8, 8))
  output = BytesIO()
  canvas.save(output, format='PNG')
  return output.getvalue()
