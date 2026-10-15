"""Build pending real evidence, then test only using actual independent review."""
import copy,json,sys,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path.insert(0,str(ROOT.parents[1]/'evidence-paper-workflow'/'scripts'))
from pdf_evidence import render_proof,binding,pdf_evidence_errors
def box(x0,y0,x1,y1):
    return [round(v*524.4000244140625/1343,3) for v in [x0,y0,x1,y1]]

def save(name,data): (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
table=json.loads((HERE/'table-transcription.json').read_text(encoding='utf-8'))
table['table_bbox']=box(130,430,1205,1645)
cell=next(c for c in table['cells'] if c['id']=='physical-r7-c1')
notes=[dict(n,applies_to_cell=n['id'] in ['1','4'],scope={'1':'승수부여 관계로 표 전체 총계 불일치 가능','2':'주수입원 형태','3':'주관적 경제평가','4':'신체적 부양자','5':'신체적 부양 만족정도','6':'정서적 부양자','7':'정서적 부양 만족정도','8':'별표가 있는 행 집단의 통계 유의성'}[n['id']]) for n in table['notes']]
trace={'value':'49.54','bbox':cell['bbox'],'row_index':6,'column_index':0,
 'row_headers':[{'text':'지역','span':[5,6],'bbox':box(142,1025,214,1054)},{'text':'군부','span':[6,6],'bbox':box(240,1055,299,1083)}],
 'column_headers':[{'text':'신체적 부양자','span':[0,2],'bbox':box(325,785,628,819)},{'text':'없음','span':[0,0],'bbox':box(333,821,411,858)}],
 'unit':{'text':'%','status':'printed','bbox':box(1100,450,1201,480)},'notes':notes,
 'population_scope':'주석4: 일상생활 수행에 제한을 받고 있는 노인에 대한 분포. 그 중 지역=군부, 신체적 부양자=없음. 계(명)의 괄호 인원261과 백분율49.54를 구분한다.'}
e={'id':'ET-C1','source_id':'LEE1994','author':'scan_table_source','quote':'49.54','context':'표2 신체적 부양자, 지역 군부, 없음. 백분율49.54; 있음50.46; 계100.00(261). 주석1·4 적용.',
 'excerpt_kind':'table','citation_type':'direct','transcription_method':'manual_visual','transcription_note':'원본 스캔 셀을 시각 대조하여49.54로 전사. raw OCR4954를 별도 보존. 독립 판정 대기.',
 'locator':{'kind':'pdf','pdf_page':5,'printed_page':'7','bbox':cell['bbox'],'context_bbox':table['table_bbox']},
 'table_context':{'label':'표2','row':'지역 > 군부','column':'신체적 부양자 > 없음','unit':'%','cell_trace':trace},'pdf_review':{'verdict':'pending'}}
proof=render_proof(HERE/'article.pdf',e['locator'],HERE/'C1-proof.png',dpi=150)
proof['crop_path']='tasks/source/C1-proof.png'
save('evidence-candidate.json',e)
review_path=ROOT/'tasks/reviewer/review.json'
def contained(relative):
    p=(ROOT/relative).resolve()
    if not p.is_relative_to(ROOT):raise ValueError('outside research root')
    return p
pending=pdf_evidence_errors(HERE/'article.pdf',e,contained)
result={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pending_candidate_errors':pending,'source':'actual original scanned scholarly PDF','review_input':str(review_path),'tests':[],'status':'pending_independent_review'}
if not review_path.is_file():
    save('gate-test-results.json',result); print(result['status']);sys.exit(0)
review=json.loads(review_path.read_text(encoding='utf-8'))
cases=review.get('cases',review.get('reviews',[]))
c=next((c for c in cases if c.get('id',c.get('claim_id'))=='C1'),None)
if not c or c.get('verdict')!='pass':
    result['actual_review']=c;save('gate-test-results.json',result);print('C1 not independently passed');sys.exit(0)
e['pdf_review']={'reviewer':review.get('reviewer',c.get('reviewer')),'timestamp':review.get('timestamp',c.get('timestamp')),'verdict':c['verdict'],'rationale':c['rationale'],'checked_features':c['checked_features'],'proof':proof,'evidence_binding':binding(e)}
save('evidence-reviewed.json',e)
def run(name,obj,expected):
    errors=pdf_evidence_errors(HERE/'article.pdf',obj,contained)
    result['tests'].append({'id':name,'expected':expected,'actual':'blocked' if errors else 'pass','matches_expectation':bool(errors)==(expected=='blocked'),'errors':errors,'review_binding_recomputed':False})
run('actual_correct_C1',e,'pass')
mutations=[('stale_quote',lambda x:x.update(quote='4954')),
 ('raw_ocr',lambda x:x.update(transcription_method='ocr')),
 ('row_index_outside_span',lambda x:x['table_context']['cell_trace'].update(row_index=7)),
 ('bad_unit',lambda x:x['table_context'].update(unit='명')),
 ('missing_notes',lambda x:x['table_context']['cell_trace'].update(notes=[])),
 ('missing_cell_trace',lambda x:x['table_context'].pop('cell_trace')),
 ('header_outside_context',lambda x:x['table_context']['cell_trace']['row_headers'][0].update(bbox=[1,1,20,20]))]
for name,mutate in mutations:
    bad=copy.deepcopy(e);mutate(bad);run(name,bad,'blocked')
result['actual_review']=c;result['status']='completed' if all(t['matches_expectation'] for t in result['tests']) else 'failed'
result['independent_semantic_cases']=[{'id':v.get('id'),'verdict':v.get('verdict'),'rationale':v.get('rationale'),'gate_action':'eligible_for_structural_checks' if v.get('verdict')=='pass' else 'blocked_by_independent_review'} for v in cases]
result['limitation']='Mutation evidence retains actual original review binding; stale review is expected. No synthetic reviewer pass assigned to mutations. Structural errors are separately visible in errors.'
save('gate-test-results.json',result);print(result['status'])
