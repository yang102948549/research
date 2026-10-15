"""Score a real independent reviewer output; preserve it as a technical test task."""
import hashlib
import json
import shutil
from pathlib import Path
from workflow import Ledger

def main():
    skill=Path(__file__).resolve().parents[1]
    stage=skill.parent/'pilot-staging'
    root=Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
    review=json.loads((stage/'tasks/semantic-evaluation/review.json').read_text(encoding='utf-8-sig'))
    expected=json.loads((skill/'tests/semantic-expected.json').read_text(encoding='utf-8'))
    actual={case['id']:case['verdict'] for case in review['cases']}
    if review['source_sha256']!=hashlib.sha256((root/'sources/article.xml').read_bytes()).hexdigest():
        raise ValueError('Reviewer input does not match canonical original')
    if set(actual)!=set(expected):
        raise ValueError('Missing or unexpected evaluation cases')
    results={cid:{'expected':expected[cid],'actual':actual[cid],'match':expected[cid]==actual[cid]} for cid in expected}
    target=root/'tasks/semantic-evaluation'
    target.mkdir(parents=True,exist_ok=True)
    for name in ('review.json','handoff.json'):
        data=(stage/'tasks/semantic-evaluation'/name).read_bytes()
        dest=target/name
        if dest.exists() and dest.read_bytes()!=data:
            raise ValueError('Do not replace already recorded reviewer artifact')
        dest.write_bytes(data)
    score={'cases':results,'matched':sum(x['match'] for x in results.values()),'total':len(results),
           'reviewer':review['reviewer_id'],'scope':'behavioral evaluation, not study approval or finished manuscript',
           'limits':'One same-model reviewer and small hand-authored evaluation. XML cell checks, no visual PDF/OCR testing.'}
    (target/'score.json').write_text(json.dumps(score,ensure_ascii=False,indent=2),encoding='utf-8')
    ledger=Ledger(root)
    handoff=json.loads((target/'handoff.json').read_text(encoding='utf-8-sig'))
    ledger.commit_handoff(handoff)
    print(json.dumps({'matched':score['matched'],'total':score['total'],
                      'question_gate':ledger.gate('research_question')},ensure_ascii=False))

if __name__=='__main__': main()
