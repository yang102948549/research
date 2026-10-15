import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from workflow import Ledger, WorkflowError


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.tmp.cleanup)
        self.w = Ledger(self.tmp.name, 'test')
        self.file = Path(self.tmp.name) / 'source.txt'
        self.file.write_text('Association does not establish causation.', encoding='utf-8')
        self.source = dict(identity_status='matched', identity_check={'provider': 'fixture', 'title_match': True},
            fulltext_status='available', parse_status='checked', path='source.txt',
            file_hash=hashlib.sha256(self.file.read_bytes()).hexdigest())
        self.w.put('sources', 'p1', self.source)
        self.w.put('evidence', 'e1', dict(source_id='p1', source_hash=self.w.data['sources']['p1']['hash'],
            quote='Association does not establish causation.', context='Methodological limit.',
            limits='Synthetic unit test only.', locator={'kind': 'html', 'section': 'Limits', 'paragraph': 1},
            quote_check='source_compared'))
        self.w.put('claims', 'c1', dict(text='Association is insufficient for causation.', author='writer', evidence_ids=['e1']))
        self.w.put('paragraphs', 'para1', dict(text='Association is insufficient for causation.', author='writer', claim_ids=['c1']))
        self.w.set_plan('research_question', 'What can association establish?')
        self.w.set_plan('outline', ['c1'])
        self.w.record_feasibility(['p1'], 'Identified preliminary source addresses the question.')

    def approve(self):
        for gate in ('research_question', 'outline'):
            self.w.approve(gate, {'explicit': True, 'message_id': 'test-fixture-approval'})

    def test_pass_requires_semantic_review_and_both_approvals(self):
        self.assertFalse(self.w.gate('final')['pass'])
        self.approve()
        self.assertFalse(self.w.gate('final')['pass'])
        self.w.review('c1', 'independent-reviewer', 'pass', 'Compared original: no causal inference.')
        self.w.review_paragraph('para1', 'independent-reviewer', 'pass', 'All factual statements match claim and source.')
        self.assertTrue(self.w.gate('manuscript')['pass'])
        self.assertFalse(self.w.gate('final')['pass'])
        self.w.record_export_validation('source.txt', dict(structure_valid=True,
            content_reextracted=True, citation_alignment=True, material_unresolved=[], visual_status='not_completed'))
        self.assertFalse(self.w.gate('final')['pass'])  # single dummy export is not a complete bundle
        self.assertEqual(self.w.data['reviews']['c1']['review_kind'], 'agent_reviewed')

    def test_fake_or_wrong_doi_identity_rejected(self):
        for status in ('not_found', 'conflict'):
            self.w.put('sources', 'p1', dict(self.source, identity_status=status))
            self.assertTrue(self.w.source_errors('p1'))
            with self.assertRaises(WorkflowError):
                self.w.review('c1', 'reviewer', 'pass', 'Unsupported claim')

    def test_abstract_only_cannot_pass(self):
        self.w.put('sources', 'p1', dict(self.source, fulltext_status='abstract_only'))
        self.assertIn('full text unavailable (abstract is insufficient)', self.w.source_errors('p1'))

    def test_no_self_review_or_automatic_semantics(self):
        with self.assertRaises(WorkflowError):
            self.w.review('c1', 'writer', 'pass', 'Self-approved')
        self.approve()
        self.w.review('c1', 'independent', 'revise', 'Claim reverses source or overstates causality')
        self.assertFalse(self.w.gate('final')['pass'])

    def test_mutation_invalidates_prior_decisions(self):
        self.approve()
        self.w.review('c1', 'reviewer', 'pass', 'Compared source')
        self.w.set_plan('outline', ['c1', 'new argument'])
        self.assertFalse(self.w.gate('final')['pass'])
        self.assertFalse(self.w.data['reviews'])
        self.assertFalse(self.w.approved('outline'))

    def test_drafting_keeps_plan_approvals_but_requires_new_review(self):
        self.approve()
        self.w.review('c1', 'reviewer', 'pass', 'Checked original')
        self.w.put('paragraphs', 'para1', dict(text='Reworded interpretation', claim_ids=['c1']))
        self.assertTrue(self.w.approved('research_question'))
        self.assertTrue(self.w.approved('outline'))
        self.assertFalse(self.w.gate('final')['pass'])

    def test_same_version_stale_write_rejected(self):
        self.w.save()
        stale = Ledger(self.tmp.name)
        self.approve()
        self.w.save()
        with self.assertRaises(WorkflowError):
            stale.save()

    def test_source_bytes_changed_detected(self):
        self.file.write_text('Altered source', encoding='utf-8')
        self.assertIn('source file missing or hash mismatch', self.w.evidence_errors('e1'))

    def test_locator_and_parse_failures(self):
        e = dict(self.w.data['evidence']['e1'])
        e['locator'] = {'kind': 'html', 'section': 'x', 'paragraph': 1, 'printed_page': 2}
        self.w.put('evidence', 'e1', e)
        self.assertIn('Do not invent HTML printed pages', self.w.evidence_errors('e1'))
        self.w.put('sources', 'p1', dict(self.source, parse_status='failed'))
        self.assertIn('parsing unchecked or failed', self.w.source_errors('p1'))

    def handoff(self):
        return dict(research_id='test', task_id='t1', role='review', input_version=self.w.data['version'],
            artifact_paths=['source.txt'], paper_ids=['p1'], evidence_ids=['e1'], unresolved=[],
            verification_status='pending', next_task='coordinator')

    def test_handoff_idempotency_staleness_and_path_containment(self):
        h = self.handoff()
        self.assertTrue(self.w.commit_handoff(h))
        self.assertFalse(self.w.commit_handoff(h))
        with self.assertRaises(WorkflowError):
            self.w.commit_handoff(dict(h, next_task='different'))
        for change in (dict(task_id='t2', input_version=-1), dict(task_id='t2', artifact_paths=['../outside'])):
            with self.assertRaises(WorkflowError):
                self.w.commit_handoff(dict(h, **change))

    def test_repairs_persist_and_limit(self):
        self.w.repair('evidence')
        self.w.set_plan('outline', ['fix attempt'])
        self.w.repair('evidence')
        loaded = Ledger(self.tmp.name)
        with self.assertRaises(WorkflowError):
            loaded.repair('evidence')

    def test_feasibility_is_required(self):
        self.approve()
        self.w.data.pop('feasibility')
        self.assertFalse(self.w.gate('research_question')['pass'])

    def test_arbitrary_paragraph_fact_does_not_inherit_claim_review(self):
        self.approve()
        self.w.review('c1', 'reviewer', 'pass', 'Claim checked')
        self.assertFalse(self.w.gate('manuscript')['pass'])
        self.w.review_paragraph('para1', 'reviewer', 'revise', 'Additional fact unsupported')
        self.assertFalse(self.w.gate('manuscript')['pass'])

    def test_committed_artifact_modification_detected(self):
        h = self.handoff()
        self.w.commit_handoff(h)
        self.file.write_text('modified after commit', encoding='utf-8')
        with self.assertRaises(WorkflowError):
            self.w.commit_handoff(h)

    def test_xml_locator_supported(self):
        self.file.write_text('<article><body><sec id="sec1"><title>Limits</title><p>Association does not establish causation.</p></sec></body></article>', encoding='utf-8')
        self.w.put('sources', 'p1', dict(self.source, file_hash=hashlib.sha256(self.file.read_bytes()).hexdigest()))
        e = dict(self.w.data['evidence']['e1'])
        e['source_hash'] = self.w.data['sources']['p1']['hash']
        e['locator'] = dict(kind='xml', section='sec1', paragraph=1)
        self.w.put('evidence', 'e1', e)
        self.assertEqual(self.w.evidence_errors('e1'), [])
        e['quote'] = 'An invented statement'
        self.w.put('evidence', 'e1', e)
        self.assertIn('XML quote absent at original source locator', self.w.evidence_errors('e1'))

    def test_missing_author_and_empty_paragraph_cannot_be_reviewed(self):
        p = dict(self.w.data['paragraphs']['para1'])
        p['text'] = '  '
        self.w.put('paragraphs', 'para1', p)
        with self.assertRaises(WorkflowError):
            self.w.review_paragraph('para1', 'reviewer', 'pass', 'Attempt')
        self.assertFalse(self.w.gate('manuscript')['pass'])
        c = dict(self.w.data['claims']['c1'])
        c.pop('author')
        self.w.put('claims', 'c1', c)
        with self.assertRaises(WorkflowError):
            self.w.review('c1', 'reviewer', 'pass', 'Attempt')
        p['text'] = 'Nonempty'
        p.pop('author')
        self.w.put('paragraphs', 'para1', p)
        with self.assertRaises(WorkflowError):
            self.w.review_paragraph('para1', 'reviewer', 'pass', 'Attempt')

    def test_resume_preserves_outputs(self):
        self.w.data['tasks']['interrupted'] = {'status': 'running', 'artifact_paths': ['source.txt']}
        self.w.save()
        resumed = Ledger(self.tmp.name)
        self.assertEqual(resumed.resume(), ['interrupted'])
        self.assertTrue(self.file.exists())
        self.assertEqual(resumed.data['tasks']['interrupted']['status'], 'pending')

    def test_worker_cannot_save_and_stale_writer_rejected(self):
        self.w.save()
        worker = Ledger(self.tmp.name, actor='writer')
        with self.assertRaises(WorkflowError):
            worker.save()
        stale = Ledger(self.tmp.name)
        self.w.set_plan('outline', ['changed'])
        self.w.save()
        with self.assertRaises(WorkflowError):
            stale.save()


if __name__ == '__main__':
    unittest.main()
