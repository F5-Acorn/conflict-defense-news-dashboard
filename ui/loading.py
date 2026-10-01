'''최초 데이터 준비와 브라우저 컴포넌트가 공유하는 로딩 표시.'''

from html import escape
from pathlib import Path

LOADING_CSS = (Path(__file__).with_name('frontend') / 'loading.css').read_text(
  encoding='utf-8'
)


def loading_html(message, *, initial=False):
  extra = ' dashboard-initial-loading' if initial else ''
  return f'''<div class="dashboard-loading{extra}" role="status" aria-live="polite">
               <span class="dashboard-spinner" aria-hidden="true"></span>
               <span class="dashboard-loading-message">{escape(message)}</span>
             </div>'''
