import sys
import tempfile
import unittest
import zipfile
import hashlib
import copy
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export import make_hwpx, text_of_hwpx, validate_hwpx, export_bundle, validate_reference, verify_export_alignment
from workflow import WorkflowError, Ledger


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_template_roundtrip_korean_special_characters(self):
        lines = ['한국어 제목', '인과가 아니다: <표> & "인용"', '공백  둘 · 기호 ≥ 0.5', '']
        path = self.root / 'test.hwpx'
        result = make_hwpx(lines, path)
        self.assertEqual(text_of_hwpx(path), lines)
        self.assertEqual(result['text_roundtrip'], 'pass')
        self.assertEqual(result['visual_review'], 'not_performed')
        with zipfile.ZipFile(path) as z:
            self.assertEqual(z.infolist()[0].filename, 'mimetype')
            self.assertEqual(z.infolist()[0].compress_type, zipfile.ZIP_STORED)
        with self.assertRaises(WorkflowError):
            validate_hwpx(path, ['different expected content'])

    def test_missing_normalized_reference_blocks_export(self):
        # Fake gate isolates exporter's own reference validation from engine.
        ledger = SimpleNamespace(root=self.root, gate=lambda name: {'pass':True}, data={
            'paragraphs': {'p': {'text':'주장', 'claim_ids':['c']}},
            'claims': {'c': {'evidence_ids':['e']}},
            'evidence': {'e': {'source_id':'s'}},
            'sources': {'s': {'citation_label':'Kim, 2020'}}})
        with self.assertRaisesRegex(WorkflowError, 'Normalized reference missing'):
            export_bundle(ledger)
        self.assertFalse((self.root / 'manuscript.hwpx').exists())

    def test_failed_manuscript_gate_blocks_all_outputs(self):
        ledger = SimpleNamespace(root=self.root, gate=lambda name: {'pass':False, 'errors':['unsupported claim']})
        with self.assertRaisesRegex(WorkflowError, 'Export blocked'):
            export_bundle(ledger)
        self.assertFalse(list(self.root.iterdir()))

    def source(self):
        return dict(title='Synthetic association study', authors=['Kim'], year=2020, doi='10.1234/synthetic',
            citation_label='Kim, 2020', reference_text='Kim, J. (2020). Synthetic association study. https://doi.org/10.1234/synthetic',
            csl={'title':'Synthetic association study', 'author':[{'family':'Kim','given':'J'}],
                 'issued':{'date-parts':[[2020]]}, 'DOI':'10.1234/synthetic'},
            bibtex='@article{S001, title = {Synthetic association study}, author = {Kim, J}, year = {2020}, doi = {10.1234/synthetic}}')

    def test_wrong_doi_in_each_normalized_reference_rejected(self):
        for location in ('csl', 'bibtex', 'reference_text'):
            s = copy.deepcopy(self.source())
            if location == 'csl':
                s['csl']['DOI'] = '10.1371/journal.pone.0069841'
            else:
                s[location] = s[location].replace('10.1234/synthetic', '10.1371/journal.pone.0069841')
            with self.subTest(location=location), self.assertRaisesRegex(WorkflowError, 'DOI mismatch'):
                validate_reference('S001', s)

    def test_wrong_title_author_year_and_missing_metadata_rejected(self):
        for field, value in [('title','Different paper'), ('authors',['Lee']), ('year',2021)]:
            s = self.source()
            s[field] = value
            with self.subTest(field=field), self.assertRaises(WorkflowError):
                validate_reference('S001', s)
        s = self.source()
        del s['title']
        with self.assertRaises(WorkflowError):
            validate_reference('S001', s)

    def test_synthetic_entire_bundle_final_gate_and_serialized_tamper(self):
        """Synthetic approvals/reviews test machinery, never a real research approval."""
        original = self.root / 'original.txt'
        original.write_text('Association is not causation.', encoding='utf-8')
        w = Ledger(self.root, 'SYNTHETIC-TEST-NOT-RESEARCH')
        source = self.source()
        source.update(identity_status='matched', identity_check='synthetic fixture only',
            fulltext_status='available', parse_status='checked', path='original.txt',
            file_hash=hashlib.sha256(original.read_bytes()).hexdigest())
        w.put('sources','S001',source)
        w.put('evidence','E001',dict(source_id='S001',source_hash=w.data['sources']['S001']['hash'],
            quote='Association is not causation.',context='Synthetic fixture.',limits='No real finding.',
            locator={'kind':'html','section':'fixture','paragraph':1},quote_check='source_compared'))
        w.put('claims','C001',dict(text='상관은 인과가 아니다',author='synthetic-writer',evidence_ids=['E001']))
        w.put('paragraphs','P001',dict(text='상관은 인과가 아니다',author='synthetic-writer',claim_ids=['C001']))
        w.set_plan('research_question','Synthetic machinery test?')
        w.set_plan('outline',['C001'])
        w.record_feasibility(['S001'],'Synthetic fixture feasibility only')
        for gate in ('research_question','outline'):
            w.approve(gate,{'explicit':True,'message_id':'SYNTHETIC-TEST-APPROVAL-NOT-HUMAN'})
        w.review('C001','synthetic-reviewer','pass','Synthetic unit fixture judgment only')
        w.review_paragraph('P001','synthetic-reviewer','pass','Synthetic unit fixture paragraph judgment only')
        self.assertTrue(w.gate('manuscript')['pass'])
        report = export_bundle(w,'합성 통합 시험')
        self.assertEqual(report['citation_reference_match'],'pass')
        self.assertTrue(Ledger(self.root).gate('final')['pass'])
        for name in ('evidence.csv', 'references.csl.json', 'references.bib', 'manuscript-trace.json', 'export-validation.json'):
            artifact = self.root / name
            original_bytes = artifact.read_bytes()
            artifact.write_bytes(original_bytes + b'\nTAMPER')
            with self.subTest(tampered=name):
                self.assertFalse(Ledger(self.root).gate('final')['pass'])
            artifact.write_bytes(original_bytes)
        self.assertTrue(Ledger(self.root).gate('final')['pass'])
        csv_path = self.root/'evidence.csv'
        csv_path.write_text(csv_path.read_text(encoding='utf-8-sig').replace('S001','OTHER'),encoding='utf-8-sig')
        with self.assertRaisesRegex(WorkflowError,'ID mismatch'):
            verify_export_alignment(self.root,w.data['sources'],{'S001'})


if __name__ == '__main__':
    unittest.main()
