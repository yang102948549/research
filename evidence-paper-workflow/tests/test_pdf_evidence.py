import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from workflow import Ledger, WorkflowError
from pdf_evidence import binding, render_proof
from parsing import pdf_blocks
try:
    import fitz
except ImportError:
    fitz=None

@unittest.skipUnless(fitz, 'PyMuPDF unavailable')
class PdfEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.path=self.root/'source.pdf'
        with fitz.open() as doc:
            p=doc.new_page(width=500,height=700)
            p.insert_text((30,60),'Evidence does not establish causation.')
            p.insert_text((30,120),'Extension 20% 2,000 square meters')
            doc.save(self.path)
        self.w=Ledger(self.root,'synthetic-pdf-gates')
        self.w.put('sources','s',dict(path='source.pdf',file_hash=hashlib.sha256(self.path.read_bytes()).hexdigest(),
            identity_status='matched',identity_check={'scope':'synthetic unit fixture'},fulltext_status='available',parse_status='checked'))
        self.e=dict(source_id='s',source_hash=self.w.data['sources']['s']['hash'],author='extractor',
            quote='Evidence does not establish causation.',context='Causal limitation.',limits='Synthetic fixture only.',
            quote_check='source_compared',excerpt_kind='prose',transcription_method='native_text',citation_type='direct',
            locator=dict(kind='pdf',pdf_page=1,printed_page=None,bbox=[25,40,350,70],context_bbox=[20,30,400,135]))
        proof=render_proof(self.path,self.e['locator'],self.root/'crop.png')
        proof['crop_path']='crop.png'
        self.e['pdf_review']=dict(reviewer='independent',timestamp='2026-10-15',verdict='pass',
            rationale='Synthetic reviewer record tests validation machinery only.',
            checked_features=['reading_order','context','negation','numbers','page_label','citation_status'],proof=proof)
        self.rebind(self.e)

    def rebind(self,e):
        e['pdf_review']['evidence_binding']=binding(e)
        self.w.put('evidence','e',e)

    def test_bound_original_passes_and_stale_quote_blocks(self):
        self.assertEqual(self.w.evidence_errors('e'),[])
        self.w.put('claims','c',dict(author='writer',text='No causal conclusion.',evidence_ids=['e']))
        self.w.review('c','independent','pass','Synthetic source comparison')
        e=copy.deepcopy(self.e)
        e['quote']='Evidence establishes causation.'
        self.w.put('evidence','e',e)
        self.assertTrue(self.w.evidence_errors('e'))
        with self.assertRaises(WorkflowError): self.w.review('c','independent','pass','Attempt')

    def test_fresh_record_cannot_make_absent_native_quote_present(self):
        e=copy.deepcopy(self.e)
        e['quote']='Evidence establishes causation.'
        self.rebind(e)
        self.assertIn('PDF quote absent from selected native-text region',self.w.evidence_errors('e'))

    def test_pdf_cannot_downgrade_locator_even_when_renamed(self):
        for filename in ('source.pdf','renamed.bin'):
            path=self.root/filename
            path.write_bytes(self.path.read_bytes())
            source=copy.deepcopy(self.w.data['sources']['s'])
            source['path']=filename
            self.w.put('sources','s',source)
            for kind in ('html','xml'):
                e=copy.deepcopy(self.e)
                e.update(source_hash=self.w.data['sources']['s']['hash'],quote='Entirely absent invented quote',
                    locator=dict(kind=kind,section='fake',paragraph=1,printed_page=None))
                e.pop('pdf_review')
                self.w.put('evidence','e',e)
                self.assertIn('PDF source requires PDF locator; format downgrade rejected',self.w.evidence_errors('e'))
                self.w.put('claims','c',dict(author='writer',text='Invented',evidence_ids=['e']))
                with self.assertRaises(WorkflowError):self.w.review('c','independent','pass','Attempt')

    def test_page_and_bbox_are_checked_against_pdf(self):
        for locator in (dict(pdf_page=999),dict(pdf_page=True),dict(bbox=[-1,0,10,10]),dict(bbox=[0,0,float('nan'),20]),dict(bbox=[400,600,500,700])):
            e=copy.deepcopy(self.e)
            e['locator'].update(locator)
            self.rebind(e)
            self.assertTrue(self.w.evidence_errors('e'))

    def test_crop_swapping_detected_even_with_new_file_hash(self):
        other=render_proof(self.path,dict(pdf_page=1,bbox=[25,100,350,130]),self.root/'other.png')
        e=copy.deepcopy(self.e)
        e['pdf_review']['proof'].update(crop_path='other.png',crop_sha256=other['crop_sha256'])
        self.rebind(e)
        self.assertIn('PDF reviewed image does not match original page region',self.w.evidence_errors('e'))

    def test_raw_ocr_and_self_review_blocked(self):
        e=copy.deepcopy(self.e)
        e['transcription_method']='ocr'
        e['pdf_review']['reviewer']='extractor'
        self.rebind(e)
        errors=self.w.evidence_errors('e')
        self.assertIn('PDF raw OCR is not approved transcription',errors)
        self.assertIn('PDF independent visual review missing/failed',errors)

    def test_table_and_footnote_context_required(self):
        for kind in ('table','footnote'):
            e=copy.deepcopy(self.e)
            e['excerpt_kind']=kind
            self.rebind(e)
            self.assertTrue(self.w.evidence_errors('e'))

    def test_spanning_body_disables_automatic_column_order(self):
        path=self.root/'mixed.pdf'
        with fitz.open() as doc:
            p=doc.new_page(width=500,height=700)
            for y in (60,110,350):
                p.insert_text((20,y),'Left column text')
                p.insert_text((300,y+20),'Right column text')
            p.insert_text((100,240),'Full width table label ' * 3)
            doc.save(path)
        record=pdf_blocks(path)['pages'][0]
        self.assertTrue(record['two_column_candidate'])
        self.assertIsNone(record['proposed_block_order'])
        self.assertIn('spanning_body_blocks_require_manual_order',record['reading_order_blockers'])

if __name__=='__main__': unittest.main()
