import json
import sys
from pathlib import Path
sys.path.insert(0,'C:/Users/USER/.codex/skills/evidence-paper-workflow/scripts')
from workflow import Ledger

root=Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
w=Ledger(root)
w.approve('outline',{'explicit':True,'message_id':'chat-user-outline-approval-2026-10-15',
 'verbatim':'이 개요 승인해. 짧은 한국어 원고 작성하고 독립 검증, HWPX 생성과 내용 재추출까지 진행해줘.'})
assert w.gate('outline')['pass'],w.gate('outline')
w.save()
paragraphs=[
 {'id':'P001','heading':'서론: 검토 대상과 방법','claim_ids':['C001'],
  'text':'이 글은 Kross 외의 연구 한 편을 대상으로, 보고된 결과와 그 결과가 허용하는 해석의 범위를 구분한다. 연구진은 14일 동안 하루 다섯 차례 문자메시지를 보내 참여자의 경험을 조사했다. 이러한 조사 절차를 검토의 출발점으로 삼되, 본고는 새로운 실증 분석이나 분야 전체의 문헌고찰을 수행하지 않는다'},
 {'id':'P002','heading':'본론: 예측 관계와 해석의 한계','claim_ids':['C002'],
  'text':'연구진은 Facebook 이용이 순간적 감정과 삶의 만족도라는 두 가지 주관적 안녕감 요소의 저하를 예측한다고 보고했다. 여기서 핵심은 저자들이 보고한 예측 관계를 정확히 전달하는 것이다. 이 결과를 모든 이용자에게 동일하게 작용하는 효과로 확대하는 해석은 해당 진술의 범위를 넘어선다'},
 {'id':'P003','heading':None,'claim_ids':['C003'],
  'text':'인과관계에 대해서는 원문이 제시한 유보를 유지해야 한다. 저자들은 연구 결과를 뒷받침하고 명확한 인과관계를 확립하려면 일상생활에서 Facebook 이용을 조작하는 실험이 필요하다고 밝혔다. 따라서 본고에서는 보고된 예측 관계를 곧바로 확정적인 인과관계로 바꾸어 서술하지 않는다'},
 {'id':'P004','heading':None,'claim_ids':['C004'],
  'text':'일반화의 범위 역시 구분할 필요가 있다. 저자들은 다른 연령집단에서도 같은 결과가 나타나는지 추가로 검토하는 일이 중요하다고 밝혔다. 이는 다른 연령집단에 대한 적용 여부가 확인되어야 한다는 뜻이며, 다른 집단에서는 관계가 성립하지 않는다고 입증했다는 뜻은 아니다'},
 {'id':'P005','heading':'결론: 근거가 허용하는 주장 범위','claim_ids':['C003','C004'],
  'text':'이 단일 논문 검토에서 유지해야 할 해석의 경계는 인과관계의 확정과 다른 연령집단으로의 일반화를 구분하는 데 있다. 전자에는 이용을 조작하는 실험이, 후자에는 해당 집단에 대한 추가 검토가 필요하다는 것이 원문이 밝힌 한계다. 이 두 한계를 함께 제시하면 연구 결과를 소개하면서도 근거가 확보되지 않은 범위까지 결론을 넓히는 일을 피할 수 있다'}]
for p in paragraphs:
    record={k:v for k,v in p.items() if k!='id'}
    record['author']='coordinator'
    w.put('paragraphs',p['id'],record)
task=root/'tasks/manuscript-draft'
task.mkdir(parents=True,exist_ok=True)
(task/'paragraphs.json').write_text(json.dumps(paragraphs,ensure_ascii=False,indent=2),encoding='utf-8')
handoff={'research_id':w.data['research_id'],'task_id':'manuscript-draft','role':'integrated-writer',
 'input_version':w.data['version'],'assigned_input_version':11,
 'reconciliation_note':'Coordinator added paragraphs under unchanged user-approved outline; semantic reviews invalidated for independent re-review.',
 'artifact_paths':['tasks/manuscript-draft/paragraphs.json'],'paper_ids':['S001'],
 'evidence_ids':['E001','E002','E003','E004'],'unresolved':[],
 'verification_status':'pending','next_task':'independent-manuscript-review'}
w.commit_handoff(handoff)
print(json.dumps({'version':w.data['version'],'paragraph_count':len(paragraphs),'outline_approved':w.approved('outline')},ensure_ascii=False))
