import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'C:/Users/USER/.codex/skills/evidence-paper-workflow/scripts')
from workflow import Ledger
from export import export_bundle,text_of_hwpx,verify_export_alignment

root=Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
stage=Path(__file__).parent/'tasks/manuscript-review'
report=json.loads((stage/'review.json').read_text(encoding='utf-8-sig'))
w=Ledger(root)
assert w.data['version']==report['input_version']
assert hashlib.sha256((root/'ledger.json').read_bytes()).hexdigest()==report['ledger_file_hash']
assert hashlib.sha256((root/'sources/article.xml').read_bytes()).hexdigest()==report['source_file_hash']
assert not report['unresolved'],report['unresolved']
assert all(r['verdict']=='pass' for r in report['claims']+report['paragraphs'])
assert {r['id'] for r in report['claims']}==set(w.data['claims'])
assert {r['id'] for r in report['paragraphs']}==set(w.data['paragraphs'])
dest=root/'tasks/manuscript-review'
dest.mkdir(parents=True,exist_ok=True)
for name in ('review.json','handoff.json'):
    data=(stage/name).read_bytes()
    if (dest/name).exists() and (dest/name).read_bytes()!=data:
        raise ValueError('Existing review differs')
    (dest/name).write_bytes(data)
for claim in report['claims']:
    w.review(claim['id'],report['reviewer_id'],claim['verdict'],claim['rationale'])
for p in report['paragraphs']:
    w.review_paragraph(p['id'],report['reviewer_id'],p['verdict'],p['rationale'])
w.commit_handoff(json.loads((dest/'handoff.json').read_text(encoding='utf-8-sig')))
assert w.gate('manuscript')['pass'],w.gate('manuscript')
output=export_bundle(w,'Facebook 이용과 주관적 안녕감: Kross 외(2013)의 주장 범위 검토')
reopened=Ledger(root)
assert reopened.gate('final')['pass'],reopened.gate('final')
verify_export_alignment(root,reopened.data['sources'],{'S001'})
assert '\n\n'.join(text_of_hwpx(root/'manuscript.hwpx'))==(root/'manuscript.md').read_text(encoding='utf-8')
cap=json.loads((root/'capabilities.json').read_text(encoding='utf-8'))
cap['outline_gate']='approved_actual_user_message'
cap['hwpx']['real_research_export']='completed_structure_text_and_reference_checks'
cap['hwpx']['visual_review']='not_performed'
(root/'capabilities.json').write_text(json.dumps(cap,ensure_ascii=False,indent=2),encoding='utf-8')
completion={'timestamp':datetime.now(timezone.utc).isoformat(),'research_id':w.data['research_id'],
 'ledger_version':w.data['version'],'claim_count':4,'paragraph_count':5,
 'manuscript_gate':reopened.gate('manuscript'),'final_gate':reopened.gate('final'),
 'hwpx_text_exactly_matches_markdown':True,'citation_reference_alignment':'pass',
 'human_reviewed':False,'visual_review':'not_performed','submission_ready':False,
 'scope':'Approved one-paper real-source pilot; not full KCI/PDF/OCR workflow coverage'}
(root/'pilot-completion.json').write_text(json.dumps(completion,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(completion,ensure_ascii=False))
