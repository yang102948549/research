from pathlib import Path
import sys,json,csv,shutil,hashlib
root=Path(__file__).parent
skill=root.parents[1]/'evidence-paper-workflow'
sys.path.insert(0,str(skill/'scripts'))
from workflow import Ledger
w=Ledger(root)
assert not w.data['approvals']
assert all(not w.evidence_errors(eid) for eid in w.data['evidence'])
for task in w.data['tasks'].values():w._check_artifacts(task)
tests=json.loads((skill/'validation-results.json').read_text(encoding='utf-8'))
assert tests['pass'] and tests['tests_run']==61
with (root/'evidence.csv').open('w',encoding='utf-8-sig',newline='') as handle:
    fields=['evidence_id','source_id','quote_original','ocr_raw','context','limits','pdf_page','printed_page','bbox','context_bbox','citation_type','reviewer','verdict','proof_path']
    writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
    for eid,e in w.data['evidence'].items():
        writer.writerow(dict(evidence_id=eid,source_id=e['source_id'],quote_original=e['quote'],ocr_raw=e.get('ocr_text_raw',''),
            context=e['context'],limits=e['limits'],pdf_page=e['locator']['pdf_page'],printed_page=e['locator'].get('printed_page'),
            bbox=json.dumps(e['locator']['bbox']),context_bbox=json.dumps(e['locator']['context_bbox']),citation_type=e['citation_type'],
            reviewer=e['pdf_review']['reviewer'],verdict=e['pdf_review']['verdict'],proof_path=e['pdf_review']['proof']['crop_path']))
report=root/'REPORT.md'
suffix='\n최종 회귀시험: 61개 통과. 스킬 형식 검사와 설치 해시 검사 통과 여부는 build-status.json/최종 실행 기록에 보존한다.\n'
if suffix not in report.read_text(encoding='utf-8'):report.write_text(report.read_text(encoding='utf-8')+suffix,encoding='utf-8')
shutil.copy2(report,skill/'references/academic-pdf-validation.md')
target=Path('C:/Users/USER/Documents/ResearchWorkspace/academic-pdf-validation-20261015')
target.mkdir(parents=True,exist_ok=True)
shutil.copytree(root,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
status=skill/'build-status.json';d=json.loads(status.read_text(encoding='utf-8'))
d['release']='0.3-academic-pdf-evidence-gates'
d['regression_tests']={'passed':61,'failed':0}
d['remaining']=['live KCI key/schema validation','complex scanned tables and broader Korean academic scan/layout corpus']
d['academic_pdf_validation']={'sources':2,'selected_evidence':7,'correct_claims_passed':7,'wrong_claims_rejected':7,'structural_mutations_blocked':10,'report':str(target/'REPORT.md')}
d['limitations']=[x for x in d['limitations'] if not x.startswith('Local Korean OCR tested')]
d['limitations'].append('Actual Korean academic text/scanned PDFs tested on selected regions; raw scan OCR year errors retained and independently corrected. Complex scanned tables unvalidated.')
status.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
# Re-open copied ledger and verify all source, proof and handoff references survived.
copied=Ledger(target)
assert all(not copied.evidence_errors(eid) for eid in copied.data['evidence'])
for task in copied.data['tasks'].values():copied._check_artifacts(task)
print(json.dumps({'research_path':str(target),'selected_evidence':len(copied.data['evidence']),'handoffs':len(copied.data['tasks']),'regression_tests':61},ensure_ascii=False))
