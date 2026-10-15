import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from parsing import pdf_blocks
from local_ocr import ocr_pdf_regions, ocr_image
try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz, 'PyMuPDF unavailable')
class PdfOcrTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'fixture.pdf'

    def test_mixed_image_header_is_not_silently_accepted(self):
        from PIL import Image
        image = Path(self.temp.name) / 'body.png'
        Image.new('RGB', (200, 300), 'white').save(image)
        with fitz.open() as doc:
            page = doc.new_page(width=300, height=400)
            page.insert_text((10, 20), 'Selectable header more than twenty characters')
            page.insert_image((10, 40, 290, 390), filename=str(image))
            doc.save(self.path)
        page = pdf_blocks(self.path)['pages'][0]
        self.assertEqual(page['status'], 'ocr_required')
        self.assertEqual(page['ocr_regions'][0]['reason'], 'raster_region_without_text')
        self.assertGreater(page['ocr_regions'][0]['bbox'][1], 20)

    def test_no_ocr_for_good_text_page(self):
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((20, 30), 'Normal selectable text long enough for extraction')
            doc.save(self.path)
        page = pdf_blocks(self.path)['pages'][0]
        with patch('local_ocr.ocr_image') as engine:
            result = ocr_pdf_regions(self.path, page)
        engine.assert_not_called()
        self.assertEqual(result['status'], 'not_requested')
        self.assertFalse(page['reading_order_verified'])

    def test_coordinates_and_never_verified(self):
        with fitz.open() as doc:
            doc.new_page(width=300, height=400)
            doc.save(self.path)
        record = {'pdf_page':1, 'ocr_regions':[{'bbox':[50, 60, 250, 300], 'reason':'test'}]}
        mocked = {'lines':[{'text':'sample','words':[{'text':'sample','bbox':[0,0,10,20]}]}], 'text':'sample'}
        with patch('local_ocr.ocr_image', return_value=mocked):
            result = ocr_pdf_regions(self.path, record, dpi=144, scratch_dir=self.temp.name)
        self.assertFalse(result['evidence_verified'])
        self.assertEqual(result['regions'][0]['lines'][0]['words'][0]['pdf_bbox'], [50,60,55,70])

    def test_engine_timeout_surfaces(self):
        import subprocess
        path = Path(self.temp.name) / 'image.png'
        path.write_bytes(b'fixture')
        with patch('local_ocr.os.name', 'nt'), patch('local_ocr.subprocess.run', side_effect=subprocess.TimeoutExpired('ocr', 1)):
            with self.assertRaises(subprocess.TimeoutExpired): ocr_image(path, timeout=1)

    def test_language_unavailable_surfaces(self):
        import subprocess
        path = Path(self.temp.name) / 'image.png'
        path.write_bytes(b'fixture')
        result = subprocess.CompletedProcess([], 1, b'', b'OCR_LANGUAGE_UNAVAILABLE:ko')
        with patch('local_ocr.os.name','nt'), patch('local_ocr.subprocess.run',return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'OCR_LANGUAGE_UNAVAILABLE'): ocr_image(path)

    def test_two_column_proposal_preserves_blocks_but_needs_review(self):
        with fitz.open() as doc:
            page = doc.new_page(width=500, height=700)
            for y in (60, 100, 140):
                page.insert_text((25, y), 'Left column paragraph')
                page.insert_text((300, y + 20), 'Right column paragraph')
            doc.save(self.path)
        record = pdf_blocks(self.path)['pages'][0]
        self.assertTrue(record['two_column_candidate'])
        self.assertEqual(set(record['proposed_block_order']), {b['block_id'] for b in record['blocks']})
        self.assertEqual(len(record['proposed_block_order']), len(record['blocks']))
        self.assertFalse(record['reading_order_verified'])

    def test_zero_page_index_rejected(self):
        with fitz.open() as doc:
            doc.new_page()
            doc.save(self.path)
        with self.assertRaisesRegex(ValueError, 'one-based'):
            ocr_pdf_regions(self.path, {'pdf_page':0,'ocr_regions':[{'bbox':[0,0,10,10]}]}, scratch_dir=self.temp.name)


if __name__ == '__main__': unittest.main()
