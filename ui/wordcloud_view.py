'''범주별 기사 수를 한글 워드클라우드로 표시한다. 아래 상수로 스타일을 조정한다.'''

import hashlib
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
  'width': 1400,
  'height': 700,
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


def wordcloud_image(frequencies):
  if not frequencies:
    return None
  # 같은 경로의 TTF가 교체된 경우에도 새 글꼴로 이미지를 생성한다.
  font_hash = hashlib.sha256(
    Path(WORDCLOUD_STYLE['font_path']).read_bytes()
  ).hexdigest()
  return _render_wordcloud(
    frequencies, WORDCLOUD_STYLE, WORDCLOUD_COLORS, WORDCLOUD_ELLIPSE, font_hash
  )


@st.cache_data(show_spinner=False, max_entries=16)
def _render_wordcloud(frequencies, style, colors, ellipse, font_hash):
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
    canvas.paste(
      words,
      ((canvas.width - words.width) // 2, (canvas.height - words.height) // 2),
    )
  output = BytesIO()
  canvas.save(output, format='PNG')
  return output.getvalue()
