import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import hwpx_tool as H  # noqa: E402

HPNS = 'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'


def rewrite_section(src, dst, transform):
    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        data = {i.filename: z.read(i.filename) for i in infos}
    data['Contents/section0.xml'] = transform(data['Contents/section0.xml'].decode('utf-8')).encode('utf-8')
    H._write(dst, infos, data)


class HwpxToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base = self.tmp / 'base.hwpx'
        H.create(['제목', '본문 첫 문단', '{{이름}} 님께'], self.base)

    def test_create_and_read_roundtrip(self):
        rows = H.read_paragraphs(self.base)
        self.assertEqual([r['text'] for r in rows], ['제목', '본문 첫 문단', '{{이름}} 님께'])
        result = H.validate(self.base, ['제목', '본문 첫 문단', '{{이름}} 님께'])
        self.assertEqual(result['text_roundtrip'], 'pass')
        self.assertEqual(result['visual_review'], 'not_performed')

    def test_inspect_lists_placeholders(self):
        info = H.inspect(self.base)
        self.assertEqual(info['placeholders'], ['{{이름}}'])
        self.assertTrue(info['mimetype_first_and_stored'])

    def test_replace_writes_new_file_and_keeps_original(self):
        out = self.tmp / 'out.hwpx'
        before = self.base.read_bytes()
        res = H.replace_text(self.base, out, {'{{이름}}': '홍길동'})
        self.assertEqual(res['replaced'], {'{{이름}}': 1})
        self.assertEqual(self.base.read_bytes(), before)
        self.assertEqual(H.read_paragraphs(out)[2]['text'], '홍길동 님께')
        H.validate(out)
        with zipfile.ZipFile(out) as z:
            self.assertIn('홍길동', z.read('Preview/PrvText.txt').decode('utf-8'))

    def test_replace_refuses_in_place_and_missing(self):
        with self.assertRaises(H.HwpxError):
            H.replace_text(self.base, self.base, {'a': 'b'})
        with self.assertRaises(H.HwpxError):
            H.replace_text(self.base, self.tmp / 'x.hwpx', {'없는말': 'b'})
        res = H.replace_text(self.base, self.tmp / 'y.hwpx', {'없는말': 'b'}, allow_missing=True)
        self.assertEqual(res['missing'], ['없는말'])

    def test_replace_across_runs_keeps_first_run_style(self):
        split = self.tmp / 'split.hwpx'

        def transform(xml):
            return xml.replace('<hp:t>{{이름}} 님께</hp:t></hp:run>',
                               '<hp:t>{{이</hp:t></hp:run><hp:run charPrIDRef="7"><hp:t>름}} 님께</hp:t></hp:run>')
        rewrite_section(self.base, split, transform)
        self.assertEqual(H.read_paragraphs(split)[2]['text'], '{{이름}} 님께')
        out = self.tmp / 'o.hwpx'
        H.replace_text(split, out, {'{{이름}}': '김'})
        self.assertEqual(H.read_paragraphs(out)[2]['text'], '김 님께')
        with zipfile.ZipFile(out) as z:
            self.assertIn('charPrIDRef="7"', z.read('Contents/section0.xml').decode('utf-8'))

    def test_table_cell_text_is_read_and_replaced_without_duplication(self):
        tabled = self.tmp / 'tbl.hwpx'

        def transform(xml):
            cell = ('<hp:p id="90" paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0">'
                    '<hp:tbl><hp:tr><hp:tc><hp:subList><hp:p id="91" paraPrIDRef="0" styleIDRef="0">'
                    '<hp:run charPrIDRef="0"><hp:t>셀값</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl>'
                    '</hp:run></hp:p>')
            return xml.replace('</hs:sec>', cell + '</hs:sec>')
        rewrite_section(self.base, tabled, transform)
        rows = H.read_paragraphs(tabled)
        self.assertEqual([r['text'] for r in rows if r['in_table']], ['셀값'])
        self.assertEqual(sum(r['text'] == '셀값' for r in rows), 1)
        out = self.tmp / 'o2.hwpx'
        H.replace_text(tabled, out, {'셀값': '바뀜'})
        self.assertIn('바뀜', [r['text'] for r in H.read_paragraphs(out)])
        self.assertEqual(H.inspect(out)['tables'], 1)

    def test_tab_child_is_a_barrier(self):
        tab = self.tmp / 'tab.hwpx'
        rewrite_section(self.base, tab, lambda xml: xml.replace(
            '<hp:t>본문 첫 문단</hp:t>', '<hp:t>앞<hp:tab/>뒤</hp:t>'))
        self.assertEqual(H.read_paragraphs(tab)[1]['text'], '앞\t뒤')
        out = self.tmp / 'o3.hwpx'
        with self.assertRaises(H.HwpxError):
            H.replace_text(tab, out, {'앞뒤': 'x'})

    def test_root_namespace_declaration_preserved(self):
        out = self.tmp / 'ns.hwpx'
        H.replace_text(self.base, out, {'제목': '새 제목'})
        with zipfile.ZipFile(self.base) as a, zipfile.ZipFile(out) as b:
            ra = a.read('Contents/section0.xml').decode('utf-8')
            rb = b.read('Contents/section0.xml').decode('utf-8')
        self.assertEqual(H._start_tag(ra), H._start_tag(rb))
        self.assertNotIn('ns0:', rb)

    def test_validate_rejects_bad_mimetype_and_non_zip(self):
        bad = self.tmp / 'bad.hwpx'
        with zipfile.ZipFile(bad, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('mimetype', b'application/hwp+zip')  # 압축됨
        with self.assertRaises(H.HwpxError):
            H.validate(bad)
        with zipfile.ZipFile(bad, 'w') as z:
            z.writestr('mimetype', b'application/hwp+zip')  # 패키지 목록 없음
        with self.assertRaises(H.HwpxError):
            H.validate(bad)
        legacy = self.tmp / 'old.hwp'
        legacy.write_bytes(b'\xd0\xcf\x11\xe0' + b'0' * 64)
        with self.assertRaises(H.HwpxError):
            H.read_paragraphs(legacy)

    def test_cli(self):
        m = self.tmp / 'm.json'
        m.write_text(json.dumps({'{{이름}}': '이'}, ensure_ascii=False), encoding='utf-8')
        out = self.tmp / 'c.hwpx'
        self.assertEqual(H.main(['replace', str(self.base), str(out), '--map', str(m)]), 0)
        self.assertEqual(H.main(['replace', str(self.base), str(out), '--old', 'zz', '--new', 'y']), 1)
        self.assertEqual(H.main(['read', str(out)]), 0)


if __name__ == '__main__':
    unittest.main()
