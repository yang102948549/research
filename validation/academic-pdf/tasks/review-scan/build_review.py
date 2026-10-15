from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
packet=json.loads((root/'packet.json').read_text(encoding='utf-8'))
source=root.parent/'scan/article.pdf'
sha=hashlib.sha256(source.read_bytes()).hexdigest()
data=[
 ('S1','pass',[47,363,253,443],'행복과 만족스러운 삶은 보장되지 못할 수 있다는 회의에서', '원문은 물질적 풍요와 높은 생활수준을 성취하더라도 행복과 만족스러운 삶이 보장되지 못할 수 있다는 회의를 소개하며 단락 끝에 (김동일·경철인, 1980: 96)을 표시한다. 다른 문헌에 기대어 소개한다는 범위와 가능성 표현을 유지한 주장이다.'),
 ('S2','revise',[47,363,253,443],'행복과 만족스러운 삶은 보장되지 못할 수 있다는 회의에서', '부정·가능성 표현을 정반대로 바꾸었다. 이 문단은 연구 발전과정을 서술하며 다른 문헌을 인용하고 있어 저자가 행복 보장을 직접 실증했다는 근거도 아니다.'),
 ('S3','pass',[273,477,480,556],'United States, 1971 ~ 1981,', '각주 1 영어 서지의 제목 끝은 1971 ~ 1981로 직접 읽힌다. 뒤의 출판연도 1973과 제목에 들어 있는 기간은 별개이다.'),
 ('S4','revise',[273,477,480,556],'United States, 1971 ~ 1981,', '실제 기간은 1971 ~ 1981이다. 제시된 7977~7987은 각 숫자를 잘못 전사한 것으로 원문과 불일치한다.'),
 ('S5','pass',[47,442,254,493],'1960년 美國에서', '왼쪽 열의 보고서 소개 문장은 1960년으로 시작한다. 이 판정은 이 논문 인쇄문자의 전사 정확성에 한하며 보고서의 실제 역사적 발행연도를 별도로 확증한 것은 아니다.'),
 ('S6','revise',[47,442,254,493],'1960년 美國에서', '원본 숫자는 1960년이다. 1%0년은 숫자 96을 퍼센트 기호처럼 잘못 읽은 표기로 원문과 불일치한다.')
]
reviews=[]
for cid,verdict,box,quote,why in data:
    reviews.append({'case_id':cid,'claim':next(c['claim'] for c in packet['cases'] if c['id']==cid),'verdict':verdict,'rationale':why,'locator':{'kind':'pdf','pdf_page':2,'printed_page':63,'bbox':box},'short_original_transcription':quote,'source_sha256':sha,'reviewer':'academic_twocol','author':'academic_scan/source-extraction agent (separate from reviewer)','method':'Rendered actual source PDF page 2 and three enlarged original-image crops; did not read scan evidence candidates, report or answer key.','scope':'Source fidelity only, not independent verification of cited historical facts.','human_reviewed':False})
(root/'review.json').write_text(json.dumps({'research_id':packet['research_id'],'task_id':'review-scan','reviews':reviews,'reviewed_files':['page2.png','negation.png','year.png','footnote.png'],'independence_limit':'Same-model role separation does not guarantee complete independence or hallucination-free review.'},ensure_ascii=False,indent=2),encoding='utf-8')
(root/'handoff.json').write_text(json.dumps({'research_id':packet['research_id'],'task_id':'review-scan','role':'independent_source_fidelity_reviewer','input_version':{'packet_sha256':hashlib.sha256((root/'packet.json').read_bytes()).hexdigest(),'source_sha256':sha},'output_paths':[str(root/'review.json')],'paper_ids':['scan/article.pdf'],'evidence_ids':['S1','S2','S3','S4','S5','S6'],'unresolved':['Original cited works not consulted; historical truth not independently verified.'],'verification_status':'pass S1/S3/S5; revise S2/S4/S6; no hold','next_task':'coordinator compare blinded verdicts with test expectations and gate decisions'},ensure_ascii=False,indent=2),encoding='utf-8')
print(sha)
