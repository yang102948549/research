from pathlib import Path
import json, shutil
base=Path(__file__).resolve().parents[1]
skill=base/'evidence-paper-workflow'
research=Path('C:/Users/USER/Documents/ResearchWorkspace/pilot-kross-2013')
tests=json.loads((skill/'validation-results.json').read_text(encoding='utf-8'))
assert tests['pass'] and tests['tests_run']==53
status_path=skill/'build-status.json'
d=json.loads(status_path.read_text(encoding='utf-8'))
d['release']='0.2-local-ocr-visual-validation'
d['regression_tests']={'passed':53,'failed':0}
d['remaining']=['live KCI key/schema validation','actual Korean academic two-column papers and physical/noisy scans','complex statistical tables']
d['limitations']=[x for x in d['limitations'] if not x.startswith('PDF extraction')]
d['limitations'].append('Local Korean OCR tested on exam PDF and simulated scans: selected phrases 8/10; negation and table headers fail; never automatically approved.')
d['pdf_ocr_validation']={'report':'validation/pdf-ocr/REPORT.md','selected_phrase_matches':8,'selected_phrase_total':10,'table_status':'failed_headers','scope':'exam PDF and simulated scans; not real academic/physical scan corpus'}
d['hwpx_visual_validation']={'status':'checked','application':'Hangul 2022','pages':1,'report':str(research/'validation/hwpx/visual-review.json')}
status_path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
# Keep copyrighted source-derived fixtures in research records, excluded by installer.
shutil.copytree(skill/'validation/pdf-ocr',research/'validation/pdf-ocr',dirs_exist_ok=True)
shutil.copy2(skill/'validation/pdf-ocr/REPORT.md',skill/'references/pdf-ocr-validation.md')
cap_path=research/'capabilities.json'
cap=json.loads(cap_path.read_text(encoding='utf-8'))
cap['pdf']={'optional_local_extraction':'implemented','korean_two_column_visual_test':'exam PDF selected pages reviewed; academic corpus pending','ocr':'Windows ko local; controlled scan tests partial; failures retained','report':'validation/pdf-ocr/REPORT.md'}
cap['hwpx']['visual_review']='checked_all_1_page_native_Hangul_2022'
cap['kci']['response_schema']='official detail total omission fixed and mocked; live compatibility pending'
cap_path.write_text(json.dumps(cap,ensure_ascii=False,indent=2),encoding='utf-8')
print('Release metadata and research validation records updated.')
