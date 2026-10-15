import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from parsing import jats_blocks, confirm_xml_quote


class ParsingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'original.xml'

    def write(self, xml):
        self.path.write_text(xml, encoding='utf-8')

    def test_inline_markup_korean_and_exact_locator(self):
        self.write('<article><body><sec id="s1"><title>한계</title><p>상관은 <italic>인과</italic>가 아니다 &amp; 추가 검토.</p><p>둘째 문단</p></sec></body></article>')
        result = jats_blocks(self.path)
        self.assertEqual(result['blocks'][0]['text'], '상관은 인과가 아니다 & 추가 검토.')
        self.assertEqual(result['parse_status'], 'needs_reading_order_review')
        locator = dict(section='s1', paragraph=1)
        self.assertTrue(confirm_xml_quote(self.path, locator, '상관은 인과가 아니다'))
        self.assertFalse(confirm_xml_quote(self.path, locator, '상관은 인과다'))
        self.assertFalse(confirm_xml_quote(self.path, dict(section='s1', paragraph=2), '상관은 인과가 아니다'))

    def test_abstract_only_and_entities_rejected(self):
        self.write('<article><front><abstract><p>Only abstract</p></abstract></front></article>')
        with self.assertRaises(ValueError):
            jats_blocks(self.path)
        self.write('<!DOCTYPE article [<!ENTITY x "unsafe">]><article><body/></article>')
        with self.assertRaises(ValueError):
            jats_blocks(self.path)

    def test_duplicate_locator_cannot_confirm_quote(self):
        self.write('<article><body><sec id="same"><p>first</p></sec><sec id="same"><p>second</p></sec></body></article>')
        self.assertFalse(confirm_xml_quote(self.path, dict(section='same', paragraph=1), 'first'))


if __name__ == '__main__':
    unittest.main()
