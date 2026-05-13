import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


DOCX_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>基层民警</w:t></w:r></w:p>
    <w:p><w:r><w:t>本地知识库</w:t></w:r></w:p>
  </w:body>
</w:document>
"""

WORKBOOK_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

WORKBOOK_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""

SHEET_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>案件</t></is></c>
      <c r="B1" t="inlineStr"><is><t>地点</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>电动车盗窃</t></is></c>
      <c r="B2" t="inlineStr"><is><t>XX小区</t></is></c>
    </row>
  </sheetData>
</worksheet>
"""

SLIDE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:txBody>
          <a:p><a:r><a:t>建设高质量数据集</a:t></a:r></a:p>
          <a:p><a:r><a:t>支撑知识库应用</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
"""


class FileParserTests(unittest.TestCase):
    def test_docx_fallback_reads_text_without_python_docx(self):
        from file_parser import parse_docx_fallback

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", DOCX_XML)

            content = parse_docx_fallback(str(path))
            self.assertIn("基层民警", content)
            self.assertIn("本地知识库", content)

    def test_excel_fallback_reads_sheet_text_without_pandas(self):
        from file_parser import parse_excel_fallback

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", WORKBOOK_XML)
                archive.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
                archive.writestr("xl/worksheets/sheet1.xml", SHEET_XML)

            content = parse_excel_fallback(str(path))
            self.assertIn("Sheet1", content)
            self.assertIn("电动车盗窃", content)

    def test_pptx_fallback_reads_slide_text_without_python_pptx(self):
        from file_parser import parse_pptx_fallback

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pptx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("ppt/slides/slide1.xml", SLIDE_XML)

            content = parse_pptx_fallback(str(path))
            self.assertIn("Slide 1", content)
            self.assertIn("建设高质量数据集", content)
            self.assertIn("支撑知识库应用", content)

    def test_pdf_parse_reports_missing_dependency_instead_of_fake_text(self):
        from file_parser import FileParseError, parse_pdf

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pdf"
            path.write_bytes(b"%PDF-1.4\n%EOF")

            with mock.patch("subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaises(FileParseError):
                    parse_pdf(str(path))


if __name__ == "__main__":
    unittest.main()
