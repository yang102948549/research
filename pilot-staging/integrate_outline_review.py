import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,'C:/Users/USER/.codex/skills/evidence-paper-workflow/scripts')
from workflow import Ledger

root=Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
stage=Path(__file__).parent/'tasks/outline-review'
report=json.loads((stage/'review.json').read_text(encoding='utf-8-sig'))
ledger=Ledger(root)
assert ledger.data['version']==report['input_version']
assert hashlib.sha256((root/'sources/article.xml').read_bytes()).hexdigest()==report['source_file_hash']
assert hashlib.sha256((root/'ledger.json').read_bytes()).hexdigest()==report['ledger_file_hash']
assert hashlib.sha256((root/'outline-v1.json').read_bytes()).hexdigest()==report['outline_file_hash']
dest=root/'tasks/outline-review'
dest.mkdir(parents=True,exist_ok=True)
for name in ('review.json','handoff.json'):
    data=(stage/name).read_bytes()
    if (dest/name).exists() and (dest/name).read_bytes()!=data:
        raise ValueError('Existing review differs')
    (dest/name).write_bytes(data)
for claim in report['claims']:
    ledger.review(claim['id'],report['reviewer_id'],claim['verdict'],claim['rationale'])
handoff=json.loads((dest/'handoff.json').read_text(encoding='utf-8-sig'))
ledger.commit_handoff(handoff)
cap=json.loads((root/'capabilities.json').read_text(encoding='utf-8'))
cap['question_gate']='approved_actual_user_reply'
cap['outline_gate']='evidence_and_independent_review_passed_awaiting_user_approval'
(root/'capabilities.json').write_text(json.dumps(cap,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'version':ledger.data['version'],'outline_gate':ledger.gate('outline')},ensure_ascii=False))
