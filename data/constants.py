'''화면 유형 이름과 DB 원값을 그대로 사용하는 판정 코드.'''

from enum import IntEnum

KIND_LABELS = {'wp': '무기', 'tech': '기술'}


class UsageCode(IntEnum):
  USED = 0
  NOT_USED = 1
  UNCERTAIN = 2


STATUS_LABELS = {
  UsageCode.USED: '사용',
  UsageCode.NOT_USED: '비사용',
  UsageCode.UNCERTAIN: '불확실',
}
