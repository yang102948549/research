from pathlib import Path
import sys,json,hashlib,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'evidence-paper-workflow/scripts'))
from workflow import Ledger
root=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
w=Ledger(root)
out=root/'tasks/coordinator/handoffs';out.mkdir(parents=True,exist_ok=True)
mapping={'twocol':(['TW-P001'],['TW-E001','TW-E002','TW-E003','TW-E004']),
         'scan':(['SCAN-KIHASA-1994-14-2-62'],['SCAN-E001','SCAN-E002','SCAN-E003'])}
for task in ('twocol','scan','review-twocol','review-scan'):
    group=task.removeprefix('review-')
    papers,evidence=mapping[group]
    original=root/'tasks'/task/'handoff.json'
    raw=json.loads(original.read_text(encoding='utf-8'))
    artifacts=[p.relative_to(root).as_posix() for p in sorted((root/'tasks'/task).iterdir()) if p.is_file()]
    for eid in evidence:assert not w.evidence_errors(eid)
    handoff=dict(research_id=w.data['research_id'],task_id=task,role='independent-review' if task.startswith('review-') else 'source-extraction-validation',
        input_version=w.data['version'],artifact_paths=artifacts,paper_ids=papers,evidence_ids=evidence,
        unresolved=['Whole-document semantic validation and original cited works outside this selected-source fidelity test.'],
        verification_status='pass',next_task='source fidelity validation complete; original OCR errors retained',
        assigned_input_version=raw.get('input_version',raw.get('입력 버전')),
        reconciliation_note='Original task-local handoff used noncanonical keys/status/version. Coordinator retained it, reconciled IDs and selected independently checked source regions against ledger version 16 and rechecked source/proof hashes. This is validation completion, not manuscript or raw OCR approval.',
        original_handoff_path=original.relative_to(root).as_posix(),
        artifact_hashes={p:sha(root/p) for p in artifacts})
    path=out/(task+'.json')
    path.write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8')
    w.commit_handoff(handoff)
# Preserve pre-fix implementation provenance before installer updates it.
old=Path('C:/Users/USER/.codex/skills/evidence-paper-workflow/scripts/workflow.py')
baseline=root/'baseline-version';baseline.mkdir(exist_ok=True)
if not (baseline/'workflow.py').exists():shutil.copy2(old,baseline/'workflow.py')
p=root/'baseline-gate.json';d=json.loads(p.read_text(encoding='utf-8'))
d['pre_fix_workflow_sha256']=sha(baseline/'workflow.py')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('4 original handoffs preserved, normalized and hash-checked; no research approvals.')
