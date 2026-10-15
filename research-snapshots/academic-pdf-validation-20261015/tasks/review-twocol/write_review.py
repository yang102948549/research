import json, hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
source=root.parent/'twocol/article.pdf'
sha=hashlib.sha256(source.read_bytes()).hexdigest()
packet=json.loads((root/'packet.json').read_text(encoding='utf8'))
spec={
'T1':('pass',2,'292',[311,548,497,595],'결과적으로 대부분의 공공도서관들이 접근성이 좋지 않은 위치에 자리 잡게 되는 경우들이 발생한 것 또한 사실이다.','오른쪽 본문 부정 표현과 일부 경우 발생이라는 원문 범위에 부합한다.'),
'T2':('revise',2,'292',[311,548,497,595],'접근성이 좋지 않은 위치','좋지 않은을 좋은으로 뒤집고 모두라는 전칭을 추가했다. 원문과 모순된다.'),
'T3':('pass',1,'291',[98,650,496,663],'이 논문은 부산대표도서관 건립 기본계획 연구(부산광역시, 2014)를 축약한 것임.','첫 번째 별표(*) 각주를 이미지로 확인했다. 2014년 연구 축약을 명시한다.'),
'T4':('revise',1,'291',[98,650,496,663],'부산대표도서관 건립 기본계획 연구(부산광역시, 2014)를 축약한 것임.','각주는 축약 연구임을 명시하므로 무관한 독립 연구라는 주장은 반대이다.'),
'T5':('pass',4,'294',[136,403,285,417],'증축 면적 | 20% | 2,000㎡','표1의 열 머리글 구분/비중/대지면적과 증축 면적 행을 교차 확인했다. 두 값과 단위가 모두 맞다.'),
'T6':('revise',4,'294',[136,403,285,417],'증축 면적 | 20% | 2,000㎡','증축 행은 20%, 2,000㎡이다. 30%, 3,000㎡는 다른 행(기준층 최대 바닥 면적 또는 주차 면적)의 값이므로 행 오연결이다.'),
'T7':('pass',4,'294',[98,466,285,479],'합계 | 100% | 10,000㎡','표1 합계 행의 대지면적 값과 제곱미터 단위를 확인했다.'),
'T8':('revise',4,'294',[98,466,285,479],'합계 | 100% | 10,000㎡','합계의 10,000을 1,000으로 축소한 수치 오류이다.')}
reviews=[]
for case in packet['cases']:
    verdict,page,printed,bbox,quote,why=spec[case['id']]
    item={'case_id':case['id'],'claim':case['claim'],'verdict':verdict,'rationale':why,
      'source_sha256':sha,'locator':{'kind':'pdf','pdf_page':page,'printed_page':printed,'bbox':bbox,
      'context_bbox':([98,345,497,480] if page==4 else bbox)},'short_visual_transcription':quote,
      'review_method':'Full original PDF page rendered at 150 dpi with PyMuPDF and visually inspected using view_image; source text search used only to refine coordinates.',
      'render_image':str(root/f'page{page}.png'),'human_reviewed':False}
    if page==4:item['table_context']={'label':'표 1','row':'증축 면적' if case['id'] in ['T5','T6'] else '합계','columns':['비중','대지면적'],'units':['%','㎡']}
    if page==1:
        item['footnote_marker']='*'
        item['locator']['printed_page']=None
        item['bibliographic_start_page']=291
        item['locator_correction']='첫쪽에는 running page label이 보이지 않는다. 291은 하단 저널 서지 291–309의 시작 쪽수이며 직접 관찰한 인쇄 쪽수와 분리한다.'
    reviews.append(item)
report={'research_id':packet['research_id'],'task_id':'review-twocol','reviewer':'academic_scan',
 'independence':'Reviewer did not collect this paper and did not read twocol evidence-candidates.json or REPORT.md. Same underlying model role separation is not full methodological independence.',
 'source':str(source),'source_sha256':sha,'scope':packet['scope'],'reviews':reviews,
 'summary':{'pass':4,'revise':4,'hold':0},'limitations':['Only designated claims and pages reviewed.','No whole-paper conclusion approval or external historical-fact verification.'],
 'corrections':[{'cases':['T3','T4'],'field':'locator.printed_page','previous':'291','current':None,'reason':'Reinspection of full page 1 confirms only bibliographic range 291–309; no displayed running page label. bibliographic_start_page=291 retained separately. Verdicts and quoted source numbers unchanged.'}]}
(root/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
handoff={'연구ID':packet['research_id'],'작업ID':'review-twocol','역할':'독립 원문·주장 대조','입력 버전':sha,
 '결과물 경로':str(root/'review.json'),'논문ID':['10.4275/KSLIS.2015.49.3.291'],'근거ID':list(spec),
 '미해결 사항':[],'검증 상태':'8 cases reviewed:4 pass,4 revise; T3/T4 printed-page locator corrected',
 'result_sha256':hashlib.sha256((root/'review.json').read_bytes()).hexdigest(),
 '다음 작업':'총괄이 검토 결과를 게이트 회귀시험과 교차 확인'}
(root/'handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf8')
