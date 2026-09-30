'''화면 내부 유형 이름과 판정 코드.'''

from enum import IntEnum

KIND_LABELS = {'wp': '무기', 'tech': '기술'}


class UsageCode(IntEnum):
  USED = 0
  NOT_USED = 1
  UNCERTAIN = 2


STATUS_LABELS = {
  UsageCode.USED: '사용',
  UsageCode.UNCERTAIN: '불확실',
  UsageCode.NOT_USED: '비사용',
}
