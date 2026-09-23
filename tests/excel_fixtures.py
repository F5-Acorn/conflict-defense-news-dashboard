'''실제 파일을 건드리지 않고 복사본의 셀만 바꾸는 테스트 도구.'''

from copy import copy
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def change_cells(path, changes):
  with ZipFile(BytesIO(path.read_bytes())) as source:
    sheet = ET.fromstring(source.read('xl/worksheets/sheet1.xml'))
    for address, value in changes.items():
      cell = sheet.find(f'.//{{{NS}}}c[@r="{address}"]')
      if cell is None:
        raise AssertionError(f'없는 셀: {address}')
      for child in list(cell):
        cell.remove(child)
      if isinstance(value, str):
        cell.set('t', 'inlineStr')
        text = ET.SubElement(ET.SubElement(cell, f'{{{NS}}}is'), f'{{{NS}}}t')
      else:
        cell.set('t', 'n')
        text = ET.SubElement(cell, f'{{{NS}}}v')
      text.text = str(value)
    with ZipFile(path, 'w') as target:
      for entry in source.infolist():
        content = (
          ET.tostring(sheet)
          if entry.filename == 'xl/worksheets/sheet1.xml'
          else source.read(entry.filename)
        )
        target.writestr(copy(entry), content)
