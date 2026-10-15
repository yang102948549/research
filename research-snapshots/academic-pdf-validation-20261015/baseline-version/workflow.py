"""Fail-closed research ledger. Semantic verdicts must come from a real reviewer.

This module validates provenance and explicit review records; it does NOT decide
whether prose is true. Only the coordinator writes this canonical ledger.
"""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone
from xml.etree.ElementTree import ParseError


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


class WorkflowError(ValueError):
    pass


class Ledger:
    REQUIRED = {'research_id', 'task_id', 'role', 'input_version', 'artifact_paths',
                'paper_ids', 'evidence_ids', 'unresolved', 'verification_status', 'next_task'}

    def __init__(self, root, research_id=None, actor='coordinator'):
        self.root = Path(root).resolve()
        self.path = self.root / 'ledger.json'
        self.actor = actor
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding='utf-8'))
            if research_id and self.data['research_id'] != research_id:
                raise WorkflowError('Research ID mismatch')
        else:
            if not research_id:
                raise WorkflowError('research_id required')
            self.data = dict(schema_version=1, research_id=research_id, version=0,
                             sources={}, evidence={}, claims={}, paragraphs={},
                             approvals={}, tasks={}, commits={}, repairs={}, reviews={},
                             outline=None, research_question=None)
        self._disk_version = self.data['version'] if self.path.exists() else None
        self._disk_hash = digest(self.data) if self.path.exists() else None

    def contained(self, path):
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise WorkflowError('Artifact escapes research directory')
        return target

    def save(self):
        if self.actor != 'coordinator':
            raise WorkflowError('Only coordinator may write canonical ledger')
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / '.ledger.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise WorkflowError('Coordinator writer lock held') from exc
        tmp = None
        try:
            os.close(fd)
            disk = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else None
            actual = disk['version'] if disk else None
            if actual != self._disk_version or (digest(disk) if disk else None) != self._disk_hash:
                raise WorkflowError('Stale ledger writer; reload before committing')
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root,
                                             delete=False) as out:
                tmp = out.name
                json.dump(self.data, out, ensure_ascii=False, indent=2)
                out.flush()
                os.fsync(out.fileno())
            # Windows sync/indexing can briefly deny replacement; retain writer lock.
            # Never delete the prior ledger to force a write, and surface persistent errors.
            for attempt in range(3):
                try:
                    os.replace(tmp, self.path)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(.1 * (attempt + 1))
            self._disk_version = self.data['version']
            self._disk_hash = digest(self.data)
        finally:
            if tmp and Path(tmp).exists():
                Path(tmp).unlink()
            lock.unlink()

    def _changed(self):
        self.data['version'] += 1
        # Reviews are conservatively invalidated, but unchanged user-approved
        # question/scope does not need approval again for ordinary drafting.
        self.data['reviews'] = {}
        self.data['paragraph_reviews'] = {}
        self.data.pop('export_validation', None)

    def record_feasibility(self, source_ids, rationale):
        if not source_ids or not rationale or any(s not in self.data['sources'] for s in source_ids):
            raise WorkflowError('Preliminary identified sources and feasibility rationale required')
        self.data['feasibility'] = dict(source_ids=source_ids, rationale=rationale,
            source_hashes={s:self.data['sources'][s]['hash'] for s in source_ids},
            question_hash=digest(self.data['research_question']), timestamp=now())

    def record_export_validation(self, artifact_path, report):
        """Record actual exporter checks, not an inferred successful export."""
        path = self.contained(artifact_path)
        if not path.is_file():
            raise WorkflowError('Export artifact missing')
        self.data['export_validation'] = dict(report, artifact_path=artifact_path,
            artifact_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
            version=self.data['version'], timestamp=now())

    def put(self, collection, item_id, record):
        if collection not in ('sources', 'evidence', 'claims', 'paragraphs'):
            raise WorkflowError('Unknown collection')
        record = json.loads(json.dumps(record))
        record.pop('hash', None)
        record['hash'] = digest(record)
        if self.data[collection].get(item_id) != record:
            self.data[collection][item_id] = record
            self._changed()
            if collection in ('sources', 'evidence', 'claims'):
                self.data['approvals'].pop('outline', None)

    def set_plan(self, field, value):
        if field not in ('research_question', 'outline'):
            raise WorkflowError('Unknown plan field')
        if self.data[field] != value:
            self.data[field] = value
            self._changed()
            self.data['approvals'].pop('outline', None)
            if field == 'research_question':
                self.data['approvals'].pop('research_question', None)

    def approve(self, gate, user_record):
        if gate not in ('research_question', 'outline') or not self.data[gate]:
            raise WorkflowError('Approval requires an existing question/outline')
        if not user_record.get('explicit') or not user_record.get('message_id'):
            raise WorkflowError('Explicit user approval evidence required')
        self.data['approvals'][gate] = dict(version=self.data['version'],
                                           content_hash=digest(self.data[gate]),
                                           user_record=user_record)

    def approved(self, gate):
        a = self.data['approvals'].get(gate, {})
        return (isinstance(a.get('version'), int) and
                a.get('content_hash') == digest(self.data[gate]))

    def source_errors(self, source_id):
        s = self.data['sources'].get(source_id)
        if not s:
            return ['missing source']
        errors = []
        if s.get('identity_status') != 'matched' or not s.get('identity_check'):
            errors.append('identity not verified against provider metadata')
        if s.get('fulltext_status') != 'available':
            errors.append('full text unavailable (abstract is insufficient)')
        if s.get('parse_status') != 'checked':
            errors.append('parsing unchecked or failed')
        try:
            path = self.contained(s.get('path', ''))
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != s.get('file_hash'):
                errors.append('source file missing or hash mismatch')
        except WorkflowError:
            errors.append('source path escapes workspace')
        return errors

    def evidence_errors(self, evidence_id):
        e = self.data['evidence'].get(evidence_id)
        if not e:
            return ['missing evidence']
        errors = self.source_errors(e.get('source_id'))
        s = self.data['sources'].get(e.get('source_id'), {})
        if e.get('source_hash') != s.get('hash'):
            errors.append('stale source version')
        locator = e.get('locator', {})
        if not e.get('quote') or not e.get('context') or not e.get('limits'):
            errors.append('quote/context/limits required')
        if locator.get('kind') == 'pdf':
            if not isinstance(locator.get('pdf_page'), int) or locator['pdf_page'] < 1:
                errors.append('PDF sequence page required')
        elif locator.get('kind') in ('html', 'xml'):
            if not locator.get('section') or not locator.get('paragraph'):
                errors.append('HTML section/paragraph required')
            if locator.get('printed_page') is not None:
                errors.append('Do not invent HTML printed pages')
        else:
            errors.append('unrecognized locator')
        if e.get('quote_check') != 'source_compared':
            errors.append('quote not compared with source')
        if locator.get('kind') == 'xml':
            try:
                from parsing import confirm_xml_quote
                if not confirm_xml_quote(self.contained(s.get('path', '')), locator, e.get('quote', '')):
                    errors.append('XML quote absent at original source locator')
            except (OSError, ValueError, KeyError, TypeError, ParseError) as exc:
                errors.append('XML quote verification failed: ' + type(exc).__name__)
        return errors

    def review(self, claim_id, reviewer, verdict, rationale, review_kind='agent_reviewed'):
        c = self.data['claims'].get(claim_id)
        if not c or not c.get('author') or not reviewer or reviewer == c.get('author'):
            raise WorkflowError('Independent identified reviewer required')
        if verdict not in ('pass', 'revise', 'hold') or not rationale:
            raise WorkflowError('Explicit semantic verdict and rationale required')
        if review_kind not in ('agent_reviewed', 'human_reviewed'):
            raise WorkflowError('Unknown review kind')
        if not c.get('evidence_ids'):
            raise WorkflowError('No supporting evidence linked')
        errors = [x for eid in c['evidence_ids'] for x in self.evidence_errors(eid)]
        if errors and verdict == 'pass':
            raise WorkflowError('; '.join(errors))
        self.data['reviews'][claim_id] = dict(reviewer=reviewer, verdict=verdict,
            rationale=rationale, review_kind=review_kind, claim_hash=c['hash'],
            version=self.data['version'], timestamp=now(),
            review_record={'reviewer': reviewer, 'verdict': verdict, 'rationale': rationale})

    def review_paragraph(self, paragraph_id, reviewer, verdict, rationale, review_kind='agent_reviewed'):
        """Reviewer identity is an orchestration convention, not authentication.

        Reviewer must compare every factual assertion in the paragraph with the
        linked claims and actual original sources; the explicit record is audit data.
        """
        p = self.data['paragraphs'].get(paragraph_id)
        if not p or not p.get('claim_ids') or not rationale or not p.get('text', '').strip():
            raise WorkflowError('Paragraph, claim links and explicit rationale required')
        claims = [self.data['claims'].get(cid) for cid in p['claim_ids']]
        if any(c is None for c in claims) or not p.get('author') or not reviewer or reviewer == p.get('author') or any(not c.get('author') or reviewer == c.get('author') for c in claims):
            raise WorkflowError('Independent identified paragraph reviewer required')
        if verdict not in ('pass', 'revise', 'hold') or review_kind not in ('agent_reviewed', 'human_reviewed'):
            raise WorkflowError('Invalid paragraph verdict/review kind')
        self.data.setdefault('paragraph_reviews', {})[paragraph_id] = dict(
            reviewer=reviewer, verdict=verdict, rationale=rationale, review_kind=review_kind,
            paragraph_hash=p['hash'], claim_hashes={cid:self.data['claims'][cid]['hash'] for cid in p['claim_ids']},
            evidence_hashes={eid:self.data['evidence'].get(eid, {}).get('hash') for c in claims for eid in c.get('evidence_ids', [])},
            version=self.data['version'], timestamp=now(),
            review_record={'reviewer': reviewer, 'verdict': verdict, 'rationale': rationale})

    def gate(self, name):
        errors = []
        f = self.data.get('feasibility', {})
        if (not f.get('rationale') or f.get('question_hash') != digest(self.data['research_question'])
                or not f.get('source_ids') or any(self.data['sources'].get(s, {}).get('identity_status') != 'matched' or self.data['sources'].get(s, {}).get('hash') != f.get('source_hashes', {}).get(s) for s in f.get('source_ids', []))):
            errors.append('research feasibility evidence missing or stale')
        if name in ('research_question', 'outline'):
            if not self.approved(name):
                errors.append('explicit approval missing or stale')
        if name in ('outline', 'manuscript', 'final'):
            outline = self.data.get('outline')
            if isinstance(outline, dict):
                outline_ids = [cid for section in outline.get('sections', []) for cid in section.get('claim_ids', [])]
                for section in outline.get('sections', []):
                    expected = {eid for cid in section.get('claim_ids', []) for eid in self.data['claims'].get(cid, {}).get('evidence_ids', [])}
                    if set(section.get('evidence_ids', [])) != expected:
                        errors.append('outline section evidence links do not match claims')
            else:
                outline_ids = outline if isinstance(outline, list) else []
            if set(outline_ids) != set(self.data['claims']):
                errors.append('outline claim IDs do not match ledger claims')
            if not self.approved('research_question'):
                errors.append('research question approval missing or stale')
            for cid, c in self.data['claims'].items():
                r = self.data['reviews'].get(cid, {})
                if not c.get('evidence_ids'):
                    errors.append(cid + ': no supporting evidence')
                if not c.get('author') or not r.get('reviewer') or r.get('reviewer') == c.get('author'):
                    errors.append(cid + ': author/reviewer identity missing or not independent')
                if r.get('verdict') != 'pass' or r.get('claim_hash') != c['hash'] or r.get('version') != self.data['version'] or not r.get('timestamp') or not r.get('review_record'):
                    errors.append(cid + ': independent semantic review missing/failed/stale')
                for eid in c.get('evidence_ids', []):
                    errors.extend(cid + ': ' + x for x in self.evidence_errors(eid))
            if not self.data['claims']:
                errors.append('no claims')
        if name in ('manuscript', 'final'):
            if not self.approved('outline'):
                errors.append('outline approval missing or stale')
            if not self.data['paragraphs']:
                errors.append('no manuscript paragraphs')
            for pid, p in self.data['paragraphs'].items():
                if not p.get('text', '').strip():
                    errors.append(pid + ': empty paragraph text')
                if not p.get('claim_ids') or any(c not in self.data['claims'] for c in p['claim_ids']):
                    errors.append(pid + ': missing claim links')
                pr = self.data.get('paragraph_reviews', {}).get(pid, {})
                if not p.get('author') or not pr.get('reviewer') or pr.get('reviewer') == p.get('author'):
                    errors.append(pid + ': author/reviewer identity missing or not independent')
                if (pr.get('verdict') != 'pass' or pr.get('paragraph_hash') != p['hash']
                        or pr.get('version') != self.data['version'] or not pr.get('timestamp') or not pr.get('review_record')):
                    errors.append(pid + ': paragraph factual fidelity not independently reviewed')
                if any(self.data['claims'].get(cid, {}).get('hash') != h for cid, h in pr.get('claim_hashes', {}).items()) or any(self.data['evidence'].get(eid, {}).get('hash') != h for eid, h in pr.get('evidence_hashes', {}).items()):
                    errors.append(pid + ': stale paragraph dependencies')
            if any(t.get('unresolved') for t in self.data['tasks'].values()):
                errors.append('unresolved handoff issues')
        if name == 'final':
            for task in self.data['tasks'].values():
                try:
                    self._check_artifacts(task)
                except WorkflowError as exc:
                    errors.append(str(exc))
            ev = self.data.get('export_validation', {})
            required_outputs = {'manuscript.hwpx', 'manuscript.md', 'evidence.csv',
                'references.bib', 'references.csl.json', 'manuscript-trace.json',
                'export-validation.json', 'hwpx-reextracted.txt', 'verification-report.md'}
            if not required_outputs.issubset(ev.get('output_hashes', {})):
                errors.append('complete export output hashes required')
            if (ev.get('version') != self.data['version'] or any(ev.get(k) is not True for k in ('structure_valid', 'content_reextracted', 'citation_alignment'))
                    or ev.get('material_unresolved') != [] or ev.get('visual_status') not in ('checked', 'not_completed')):
                errors.append('export validation missing/incomplete or material issues unresolved')
            try:
                export = self.contained(ev.get('artifact_path', ''))
                if not export.is_file() or hashlib.sha256(export.read_bytes()).hexdigest() != ev.get('artifact_hash'):
                    errors.append('export artifact missing or changed')
            except WorkflowError:
                errors.append('export artifact path invalid')
            for relative, expected in ev.get('output_hashes', {}).items():
                try:
                    output = self.contained(relative)
                    if not output.is_file() or hashlib.sha256(output.read_bytes()).hexdigest() != expected:
                        errors.append('export output missing or changed: ' + relative)
                except WorkflowError:
                    errors.append('export output path invalid: ' + relative)
        if name not in ('research_question', 'outline', 'manuscript', 'final'):
            raise WorkflowError('Unknown gate')
        return {'pass': not errors, 'errors': errors}

    def repair(self, gate, cycle_id='initial'):
        # Stable cycle IDs survive fixes. New IDs require a new externally
        # supplied input baseline; never mint one merely to bypass the limit.
        key = gate + ':' + cycle_id
        count = self.data['repairs'].get(key, 0)
        if count >= 2:
            raise WorkflowError('Repair limit: request source, report insufficient evidence, or revise thesis')
        self.data['repairs'][key] = count + 1
        self.save()

    def commit_handoff(self, handoff):
        if self.actor != 'coordinator':
            raise WorkflowError('Coordinator required')
        if self.REQUIRED - handoff.keys():
            raise WorkflowError('Missing handoff fields: ' + str(sorted(self.REQUIRED - handoff.keys())))
        tid = handoff['task_id']
        signature = digest(handoff)
        if tid in self.data['commits']:
            if self.data['commits'][tid] == signature:
                self._check_artifacts(self.data['tasks'][tid])
                return False
            raise WorkflowError('Task ID already committed with different result')
        if handoff['research_id'] != self.data['research_id'] or handoff['input_version'] != self.data['version']:
            raise WorkflowError('Stale input or wrong research')
        for key in ('artifact_paths', 'paper_ids', 'evidence_ids', 'unresolved'):
            if not isinstance(handoff[key], list):
                raise WorkflowError(key + ' must be a list')
        if not handoff['role'] or handoff['verification_status'] not in ('pending', 'pass', 'revise', 'hold'):
            raise WorkflowError('Invalid handoff role/status')
        for path in handoff['artifact_paths']:
            if not self.contained(path).is_file():
                raise WorkflowError('Missing handoff artifact')
        if any(x not in self.data['sources'] for x in handoff['paper_ids']) or any(x not in self.data['evidence'] for x in handoff['evidence_ids']):
            raise WorkflowError('Unknown handoff source/evidence ID')
        hashes = {p:hashlib.sha256(self.contained(p).read_bytes()).hexdigest() for p in handoff['artifact_paths']}
        if handoff.get('artifact_hashes') is not None and handoff['artifact_hashes'] != hashes:
            raise WorkflowError('Artifact changed since handoff was prepared')
        self.data['tasks'][tid] = dict(handoff, status='completed', artifact_hashes=hashes, committed_at=now())
        self.data['commits'][tid] = signature
        self.save()
        return True

    def _check_artifacts(self, task):
        for path, expected in task.get('artifact_hashes', {}).items():
            artifact = self.contained(path)
            if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected:
                raise WorkflowError('Committed handoff artifact missing or modified')

    def resume(self):
        resumed = []
        for tid, task in self.data['tasks'].items():
            if task.get('status') in ('running', 'interrupted'):
                task['status'] = 'pending'
                task['resume_reason'] = 'previous execution interrupted; preserve existing artifacts'
                resumed.append(tid)
        self.save()
        return resumed
