"""Actual source validation, without fabricated research approvals or manuscript."""
from pathlib import Path
import sys,copy,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'evidence-paper-workflow/scripts'))
from workflow import Ledger, now, WorkflowError
from pdf_evidence import binding,render_proof
from parsing import pdf_blocks
root=Path(__file__).parent
read=lambda p:json.loads((root/p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
twmeta=read('tasks/twocol/handoff.json')['source']
scmeta=read('tasks/scan/evidence-candidates.json')
reviews={r['case_id']:dict(r,reviewer=d.get('reviewer',r.get('reviewer'))) for name in ('twocol','scan')
         for d in [read('tasks/review-'+name+'/review.json')] for r in d['reviews']}
w=Ledger(root,'academic-pdf-validation')
for sid,folder,meta in [('TW-P001','twocol',twmeta),('SCAN-KIHASA-1994-14-2-62','scan',scmeta)]:
    path='tasks/'+folder+'/article.pdf'
    assert sha(path)==meta['sha256']
    w.put('sources',sid,dict(title=meta['title'],authors=meta['authors'],year=meta['year'],
        doi=meta.get('doi'),source_url=meta.get('url',meta.get('pdf_url')),path=path,file_hash=sha(path),
        identity_status='matched',identity_check={'method':'Official publisher PDF first-page title/author/year/journal compared by source agent',
            'record':'tasks/'+folder+'/handoff.json'},fulltext_status='available',parse_status='checked',
        parse_scope='Only selected evidence regions visually checked; whole-document reading order NOT approved'))
evidence_map={}
for sample in read('tasks/twocol/evidence-candidates.json'):
    eid=sample['evidence_id']; n=int(eid[-1]); cid='T'+str(2*n-1); rev=reviews[cid]
    kind={'negation':'prose','footnote':'footnote','table_cell':'table','table_total':'table'}[sample['type']]
    locator=copy.deepcopy(sample['locator'])
    if kind=='table':locator['context_bbox']=[90,340,510,490]
    else:locator['context_bbox']=list(locator['bbox'])
    e=dict(source_id='TW-P001',author='academic_twocol',quote=sample['original_visual_transcription'].removesuffix(' 이'),
        context=rev['rationale'],limits=sample['limits'],locator=locator,quote_check='source_compared',excerpt_kind=kind,
        transcription_method='native_text',citation_type='direct')
    if kind=='footnote':e['footnote_marker']='*'
    if kind=='table':e['table_context']=dict(label='표 1',row='증축 면적' if n==3 else '합계',column='비중 및 대지면적',unit='% 및 ㎡')
    evidence_map[cid]=(eid,e,rev)
for n,sample in enumerate(scmeta['samples'],1):
    eid=sample['evidence_id'];cid='S'+str(2*n-1);rev=reviews[cid]
    locator={k:sample[k] for k in ('pdf_page','printed_page','bbox','context_bbox')};locator['kind']='pdf'
    e=dict(source_id=scmeta['paper_id'],author='academic_scan',quote=sample['critical_text'],context=sample['original_context_ocr'],
        limits=sample['limitation']+' 원 OCR는 보존하고 독립 원본대조 후 정정된 선택 구절만 사용.',
        locator=locator,quote_check='source_compared',excerpt_kind=sample['excerpt_kind'],transcription_method='manual_visual',
        transcription_note='Actual publisher scan visually transcribed and independently checked; raw OCR not used as approved quotation.',
        ocr_text_raw=sample['original_ocr'],citation_type=sample['citation_type'])
    # Preserve raw OCR context separately; accepted context is the independently reviewed rationale.
    e['ocr_context_raw']=e['context'];e['context']=rev['rationale']
    if n==2:e['footnote_marker']='1)'
    evidence_map[cid]=(eid,e,rev)
for cid,(eid,e,rev) in evidence_map.items():
    sid=e['source_id'];source=w.data['sources'][sid]
    assert rev['source_sha256']==source['file_hash'] and rev['verdict']=='pass'
    e['source_hash']=source['hash']
    proof_path='proofs/'+eid+'.png'
    proof=render_proof(root/source['path'],e['locator'],root/proof_path)
    proof['crop_path']=proof_path
    features=['reading_order','context','negation','numbers','page_label','citation_status']
    if e['excerpt_kind']=='table':features+=['table_headers','table_units','table_notes']
    if e['excerpt_kind']=='footnote':features+=['footnote_marker']
    e['pdf_review']=dict(reviewer=rev['reviewer'],verdict='pass',timestamp=now(),rationale=rev['rationale'],
        review_record='tasks/review-'+('twocol' if cid.startswith('T') else 'scan')+'/review.json',
        checked_features=features,proof=proof,evidence_binding=binding(e))
    w.put('evidence',eid,e)
    w.put('claims',cid,dict(text=rev['claim'],author='coordinator',evidence_ids=[eid],kind='original-source-fidelity-test'))
# All changes first; then independent reviews so version dependencies remain current.
for cid,(eid,e,rev) in evidence_map.items():
    assert not w.evidence_errors(eid),(eid,w.evidence_errors(eid))
    w.review(cid,rev['reviewer'],'pass',rev['rationale'])
w.save()
results=[]
for cid,rev in reviews.items():
    original=cid if int(cid[1:])%2 else cid[0]+str(int(cid[1:])-1)
    eid=evidence_map[original][0]
    test=Ledger(root)
    test.put('claims',cid,dict(text=rev['claim'],author='coordinator',evidence_ids=[eid],kind='control-source-fidelity-test'))
    test.review(cid,rev['reviewer'],rev['verdict'],rev['rationale'])
    accepted=test.data['reviews'][cid]['verdict']=='pass' and not test.evidence_errors(eid)
    results.append(dict(case_id=cid,evidence_id=eid,verdict=rev['verdict'],accepted=accepted,rationale=rev['rationale']))
    assert accepted==(int(cid[1:])%2==1)
controls=[]
eid='TW-E003'
mutations=[('nonexistent_page',lambda e:e['locator'].update(pdf_page=9999)),
 ('wrong_bbox',lambda e:e['locator'].update(bbox=[-5,0,10,10])),
 ('changed_table_number',lambda e:e.update(quote='증축 면적 30% 3,000㎡')),
 ('removed_table_headers',lambda e:e.pop('table_context')),
 ('raw_ocr',lambda e:e.update(transcription_method='ocr')),
 ('self_review',lambda e:e['pdf_review'].update(reviewer=e['author'])),
 ('changed_printed_page',lambda e:e['locator'].update(printed_page=999)),
 ('missing_original_crop',lambda e:e['pdf_review']['proof'].update(crop_path='missing.png'))]
for name,mutate in mutations:
    test=Ledger(root); e=copy.deepcopy(test.data['evidence'][eid]);mutate(e);test.put('evidence',eid,e)
    errors=test.evidence_errors(eid);assert errors,name
    controls.append(dict(case=name,blocked=True,errors=errors))
for name in ('twocol','scan'):
    parsed=pdf_blocks(root/'tasks'/name/'article.pdf')
    (root/('reparsed-'+name+'.json')).write_text(json.dumps(parsed,ensure_ascii=False,indent=2),encoding='utf-8')
    if name=='twocol':assert parsed['pages'][3]['proposed_block_order'] is None
    else:assert parsed['pages'][1]['layout_status']=='unknown_no_native_text'
report=dict(timestamp=now(),scope='Actual academic sources, selected excerpts only; no research question/outline approvals or manuscript',
    independent_cases=results,structural_mutations=controls,correct_claims_passed=7,incorrect_claims_rejected=7,
    structural_mutations_blocked=8,source_count=2,selected_evidence_count=7,
    actual_ocr_errors_retained=['1971~1981 -> 7977~7987','1960 -> 1%0'],
    approval_status='not_requested_not_fabricated',human_reviewed=False,
    limitation='Role-separated same model review is not complete independence or proof of hallucination-free operation.')
(root/'gate-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('independent_cases','structural_mutations')},ensure_ascii=False))
