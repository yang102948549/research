from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'C:/Users/USER/.codex/skills/evidence-paper-workflow/scripts')
from workflow import Ledger
root=Path(__file__).parent
path=root/'tasks/twocol/article.pdf'
w=Ledger(root/'baseline-memory-only','baseline-memory-only')
# Set root to the artifact folder without saving a synthetic research ledger.
w.root=root
w.put('sources','p',dict(identity_status='matched',identity_check='Verified publisher original title/author/DOI',
    fulltext_status='available',parse_status='checked',path='tasks/twocol/article.pdf',file_hash=hashlib.sha256(path.read_bytes()).hexdigest()))
w.put('evidence','bad',dict(source_id='p',source_hash=w.data['sources']['p']['hash'],
    quote='This invented sentence is not in the paper.',context='Invalid control.',limits='Validation control only.',
    locator={'kind':'pdf','pdf_page':9999},quote_check='source_compared'))
errors=w.evidence_errors('bad')
report={'scope':'Pre-fix installed PDF evidence gate only; no user approval or manuscript generated',
        'control':'invented quote, nonexistent page 9999, no bbox or original-image review',
        'errors':errors,'incorrectly_accepted':not errors}
(root/'baseline-gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
